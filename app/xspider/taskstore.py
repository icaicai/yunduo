# coding=utf8

import atexit
import threading
from datetime import datetime
from celery import current_app
from celery.utils.log import get_logger

logger = get_logger('TaskStore')


class TaskStore(object):
    def __init__(self, task_name, save_kw=None, **kw):
        self.buffers = {}
        self._buffer_max_size = kw.get('size', 20)
        self._buffer_flush_timing = kw.get('interval', 2.0)
        self._task_name = task_name
        self._save_task = current_app.tasks['xspider.save_log']
        if save_kw is None:
            save_kw = {}
        if 'collection' not in save_kw:
            save_kw['collection'] = '%s_task_infos' % task_name.split('.')[-1]
        self._save_kw = save_kw

        atexit.register(self.destroy)

        # retrieving main thread as a safety

        self._buffer_lock = threading.RLock()

        # call at interval function
        # def call_repeatedly(interval, func, *args):
        main_thead = threading.current_thread()
        stopped = threading.Event()
        # actual thread function

        def loop():
            while not stopped.wait(self._buffer_flush_timing) and main_thead.is_alive():  # the first call is in `interval` secs
                self.flush_to_mongo()

        timer_thread = threading.Thread(target=loop)
        timer_thread.daemon = True
        timer_thread.start()
        # return stopped.set, timer_thread

        # launch thread
        self._timer_stopper = stopped.set
        self._timer_thread = timer_thread
        # self._timer_stopper, self.buffer_timer_thread = call_repeatedly(self.buffer_flush_timing, self.flush_to_mongo)

    def save(self, type, task_id, data):
        """Inserting new logging record to buffer and flush if necessary."""
        type, _, subject = type.partition('-')
        if type != 'task' or not data:
            return

        data[subject] = datetime.now()
        self.add_to_buffer(task_id, data)

        if len(self.buffers) >= self._buffer_max_size:
            self.flush_to_mongo()
        return

    def add_to_buffer(self, task_id, data):
        """Add a formatted record to buffer."""

        self._buffer_lock.acquire()
        try:
            if not data:
                return
            if task_id in self.buffers:
                self.buffers[task_id].update(data)
            else:
                self.buffers[task_id] = data
        finally:
            self._buffer_lock.release()

    def flush_to_mongo(self):
        """Flush all records to mongo database."""
        if len(self.buffers) > 0:
            self._buffer_lock.acquire()
            try:
                # print '$$$$$send to task %s %s %s' % (self._task_name, type(self.buffers), len(self.buffers))
                self._save_task.apply_async(('task', self._task_name, self.buffers), self._save_kw)

                # del self.buffers
                self.buffers = {}
            except Exception:
                logger.exception('flush_to_mongo')

            finally:
                self._buffer_lock.release()

    def destroy(self):
        """Clean quit logging. Flush buffer. Stop the periodical thread if needed."""
        if self._timer_stopper:
            self._timer_stopper()
        self.flush_to_mongo()
        # self.close()
