# coding=utf8

import time
import json
from celery.utils.log import get_logger
from celery import beat  # Scheduler, ScheduleEntry, DEFAULT_MAX_INTERVAL
from yunduo.resource import get_connection
from .serializer import serialize_entry, deserialize_entry


logger = get_logger('xbeat')

# entries_key = 'beat_entries'
# schedule_key = 'schedule_entries'
# redis_conf = get_connection('conf')
# redis_run = get_connection('run')


class Store(object):
    _redis = get_connection('conf')
    entries_key = 'beat_entries'
    schedule_key = 'schedule_entries'

    def __init__(self, lock_ttl=None):
        self.lock_ttl = lock_ttl
        self.lock = self._redis.lock('beat_lock', lock_ttl)

    def __getitem__(self, key):
        data = self._redis.hget(self.entries_key, key)
        if not data:
            raise KeyError()
        return deserialize_entry(json.loads(data), ScheduleEntry)

    def __setitem__(self, key, entry):
        # print('__setitem__', key, entry)
        if entry:
            self.add(entry)
        else:
            self.remove(key)
        # next_time = entry.next_time()
        # if next_time is None:
        #     score = -1
        # else:
        #     score = next_time.timestamp()
        # self._redis.zadd(self.schedule_key, entry.name, score)
        # self._redis.hset(self.entries_key, entry.name, serialize_entry(entry))

    def __iter__(self):
        if self.lock.acquire(False):
            try:
                max_score = time.time()
                keys = self._redis.zrangebyscore(self.schedule_key, 0, max_score)
                for key in keys:
                    yield self[key]
                key = self._redis.zrange(self.schedule_key, 0, 1)
                if key:
                    yield self[key[0]]
            finally:
                try:
                    self.lock.release()
                except Exception as e:
                    logger.exception('release lock')
        else:
            yield

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, key, value=None):
        if isinstance(key, dict) and value is None:
            for k in key:
                self[k] = key[k]
        else:
            self[key] = value

    @classmethod
    def add(cls, entry):
        if not isinstance(entry, ScheduleEntry):
            entry = ScheduleEntry(**entry)
        next_time = entry.next_time()
        if next_time is None:
            score = float("inf")
        else:
            score = next_time.timestamp()

        with cls._redis.pipeline() as pipe:
            pipe.zadd(cls.schedule_key, entry.name, score)
            pipe.hset(cls.entries_key, entry.name, json.dumps(serialize_entry(entry)))
            pipe.execute()

    @classmethod
    def remove(cls, entry):
        if isinstance(entry, ScheduleEntry):
            key = entry.name
        else:
            key = entry
        with cls._redis.pipeline() as pipe:
            pipe.zrem(cls.schedule_key, key)
            pipe.hdel(cls.entries_key, key)
            pipe.execute()


class ScheduleEntry(beat.ScheduleEntry):

    def __init__(self, name=None, task=None, last_run_at=None, max_run_count=None,
                 total_run_count=None, schedule=None, args=(), kwargs={},
                 options={}, relative=False, app=None):
        self.max_run_count = max_run_count
        super(ScheduleEntry, self).__init__(name, task, last_run_at, total_run_count, schedule,
                                            args, kwargs, options, relative, app)

    def __reduce__(self):
        return self.__class__, (
            self.name, self.task, self.last_run_at, self.max_run_count, self.total_run_count,
            self.schedule, self.args, self.kwargs, self.options,
        )

    def next_time(self):
        last_run_at = self.last_run_at
        if last_run_at is None:
            return self._default_now()

        delta = self.schedule.remaining_estimate(last_run_at)
        # if no delta, means no more events after the last_run_at.
        if delta is None:
            return None
        # overdue => due now
        if delta.total_seconds() < 0:
            return self._default_now()

        return last_run_at + delta

    def _next_instance(self, last_run_at=None):
        """Return new instance, with date and count fields updated."""
        if self.max_run_count and self.total_run_count >= self.max_run_count:
            return None

        return self.__class__(**dict(
            self,
            last_run_at=last_run_at or self._default_now(),
            total_run_count=self.total_run_count + 1,
        ))
    __next__ = next = _next_instance  # for 2to3

    def is_due(self):
        if self.max_run_count and self.total_run_count >= self.max_run_count:
            return False, float("inf")
        return self.schedule.is_due(self.last_run_at)

    # name = None, task = None, last_run_at = None,
    # total_run_count = None, schedule = None, args = (), kwargs = {},
    # options = {}, relative = False, app = None
    # def save(self):
    #     next_time = self.next_time()
    #     if next_time is None:
    #         score = -1
    #     else:
    #         score = next_time.timestamp()
    #     data = serialize_entry(self)
    #     redis_conf.hset(entries_key, self.name, json.dumps(data))
    #     redis_conf.zadd(schedule_key, self.name, score)
    #     # with redis(self.app).pipeline() as pipe:
    #     #     pipe.hset(self.key, 'definition', json.dumps(definition, cls=RedBeatJSONEncoder))
    #     #     pipe.zadd(self.app.redbeat_conf.schedule_key, self.score, self.key)
    #     #     pipe.execute()
    #
    #     return self

    # @classmethod
    # def from_data(cls, data, app=None):
    #     data.setdefault('app', app)
    #     entry = deserialize_entry(data, cls)
    #     return entry



class Scheduler(beat.Scheduler):

    Entry = ScheduleEntry

    # def __init__(self, *args, **kwargs):
    #     super(Scheduler, self).__init__(*args, **kwargs)

    def setup_schedule(self):
        max_loop_interval = self.app.conf.get('beat_max_loop_interval', 60)
        lock_ttl = max_loop_interval * 3
        self._store = Store(lock_ttl)
        super(Scheduler, self).setup_schedule()

    # def sync(self):
    #     self._store.sync()

    def get_schedule(self):
        return self._store

    def set_schedule(self, schedule):
        for name in schedule:
            self._store[name] = schedule[name]

    schedule = property(get_schedule, set_schedule)

    def tick(self):
        """Run a tick - one iteration of the scheduler.

        Executes one due task per call.

        Returns:
            float: preferred delay in seconds for next call.
        """
        adjust = self.adjust
        max_interval = self.max_interval

        # if (self._heap is None or
        #         not self.schedules_equal(self.old_schedulers, self.schedule)):
        #     self.old_schedulers = copy.copy(self.schedule)
        #     self.populate_heap()
        #
        # H = self._heap
        #
        # if not H:
        #     return max_interval
        #
        # event = H[0]
        # entry = event[2]
        next_time = [max_interval]
        for entry in self._store:
            is_due, next_time_to_run = self.is_due(entry)
            next_time.append(next_time_to_run)
            if is_due:
                next_entry = self.reserve(entry)
                self.apply_entry(entry, producer=self.producer)
                # self._store.update(next_entry)
                logger.info('apply entry %s', entry)

        return min(adjust(min(next_time)), max_interval)
