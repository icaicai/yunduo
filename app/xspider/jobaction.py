# coding=utf8

import time
import pickle
import requests
from kombu.utils.objects import cached_property
from yunduo.conf import xconf
from yunduo.resource import get_connection
from yunduo.rate import parse_rate
from yunduo.queue import get_job_queue, get_action_queue
from xspider.app import app as xspider_app


class Base(object):
    prefix = ''
    queue_api_uri = xconf.get('queue_api')

    @classmethod
    def from_queue_name(cls, name):
        keys = name.split(':')
        return cls(*keys[1:])

    def __init__(self, *args):
        self._task = None

    @cached_property
    def queue(self):
        raise NotImplementedError()

    @property
    def task(self):
        return self._task

    @property
    def id(self):
        return self._task and self._task.id

    def status(self):
        # base_uri = 'http://celery:passwdcelery@localhost:15672/api/queues'
        queues_uri = '{0}/%2F/{1}'.format(self.queue_api_uri, self.queue.name)

        resp = requests.get(queues_uri)
        if resp.status_code == 200:
            queues = resp.json()
            return queues

    def resume(self, **kw):
        q = self.queue
        opts = {
            'exchange': q.exchange.name,
            'routing_key': q.routing_key,
            'reply': True,
            'options': {
                'queue_arguments': q.queue_arguments,
                'consumer_arguments': q.consumer_arguments
            }
        }
        opts.update(kw)
        return xspider_app.control.add_consumer(self.queue.name, **opts)

    def stop(self, delete=True, **kw):
        r = xspider_app.control.cancel_consumer(self.queue.name, reply=True)
        if delete:
            with xspider_app.default_connection() as conn:
                result = conn.default_channel.queue_delete(self.queue.name, **kw)
                return result
        return r

    def pause(self):
        # print('==> pause', self.queue.name)
        return xspider_app.control.cancel_consumer(self.queue.name, reply=True)

    def purge(self):
        xspider_app.channel.queue_purge(self.queue.name)


class JobAction(Base):

    def __init__(self, project, job, batch_id):
        super(JobAction, self).__init__()
        self.project = project
        self.job = job
        self.batch_id = batch_id
        self.redis_run = get_connection('run')

    @cached_property
    def queue(self):
        return get_job_queue(self.project, self.job, self.batch_id)

    @cached_property
    def conf(self):
        return xconf.get_job(self.project, self.job)

    # @property
    # def status(self):
    #     pass

    def start(self, kwargs=None, **options):
        from xspider.tasks import crawl as xspider_crawl
        # queue = gen_queue_name(project, job, batch_id)
        # status = self.status

        # if status['xxx']:
        #     return False

        # cnf = conf.get_job(project, job)
        conf = self.conf
        if conf['rate_limit']:
            try:
                rate, burst = parse_rate(conf['rate_limit'])
                if rate > 0:
                    data = {
                        'timestamp': time.time(),
                        'fill_rate': rate,
                        'capacity': burst,
                        'tokens': burst
                    }
                    xconf.raw_set('rate:%s' % self.project, data)
            except Exception:
                pass

        t_kwargs = kwargs or {}
        t_kwargs['batch_id'] = self.batch_id
        if conf['rate_limit']:
            t_kwargs['__limit__'] = True
        if conf['entry_type'] == 1:
            t_args = (self.project, self.job, conf['entry_script'], None)
        else:
            t_args = (self.project, self.job, conf['entry_page'], conf['entry_url'])

        # task = xspider_app.tasks['xspider.crawl']
        status = self.redis_run.hget('queue:running', self.queue.name)
        if not status and self._task is None:
            self._task = xspider_crawl.apply_async(t_args, t_kwargs, **options)

        self.resume()
        return self._task

    def resume(self, **kw):
        # redis_run = get_connection('run')
        with self.redis_run.pipeline() as pipe:
            pipe.hset('queue:running', self.queue.name, time.time())
            pipe.hset('job:running', self.project, self.queue.name)
            pipe.execute()
        return super(JobAction, self).resume(**kw)

    def pause(self):
        # redis_run = get_connection('run')
        with self.redis_run.pipeline() as pipe:
            pipe.hset('queue:running', self.queue.name, 'pause')
            # pipe.hset('project:running', self.project)
            pipe.execute()
        return super(JobAction, self).pause()
        # return xspider_app.control.cancel_consumer(self.queue.name, reply=True)

    def stop(self, delete=True, **kw):
        # redis_run = get_connection('run')
        with self.redis_run.pipeline() as pipe:
            pipe.hdel('queue:running', self.queue.name)
            pipe.hdel('job:running', self.project)
            pipe.execute()
        return super(JobAction, self).stop(delete, **kw)

    def is_running(self):
        # redis_run = get_connection('run')
        status = self.redis_run.hget('queue:running', self.queue.name)
        if status and status != 'pause':
            return True
        return False

    def set_data(self, data):
        self.redis_run.hset('data:%s' % self.project, '%s:%s' % (self.job, self.batch_id), pickle.dumps(data))

    def get_data(self):
        data = self.redis_run.hget('data:%s' % self.project, '%s:%s' % (self.job, self.batch_id))
        if data:
            return pickle.loads(data)


class ActionAction(Base):

    def __init__(self, project, action, batch_id):
        super(ActionAction, self).__init__()
        self.project = project
        self.action = action
        self.batch_id = batch_id

    @cached_property
    def queue(self):
        return get_action_queue(self.project, self.action)

    @cached_property
    def conf(self):
        return xconf.get_action(self.project, self.action)

    # @property
    # def status(self):
    #     pass

    @property
    def multistage(self):
        return self.conf.get('multistage', False)

    @property
    def timeout(self):
        return self.conf.get('timeout', 60)

    @property
    def id(self):
        return self._task.id

    def start(self, kwargs=None, **options):
        from xspider.tasks import action as xspider_action

        # if status['xxx']:
        #     return False

        t_kwargs = kwargs or {}
        t_kwargs.update({
            'batch_id': self.batch_id
        })
        # options.setdefault('time_limit', 600)
        # task = xspider_app.tasks['xspider.action']
        t_args = (self.project, self.action)
        if self._task is None:
            self._task = xspider_action.apply_async(t_args, t_kwargs, **options)
        self.resume()
        return self._task

    def get(self, *args, **kwargs):
        kwargs.setdefault('timeout', self.timeout)
        return self._task.get(*args, **kwargs)

# Action 是由 xapi 来调用的，需要即时放回结果，不需要暂停，不需要停止
