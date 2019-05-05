# coding=utf8

import sys
import traceback
import atexit
import threading
import logging
from datetime import datetime
from collections import deque
from kombu.utils.objects import cached_property
from celery._state import get_current_task
from celery.utils.log import get_task_logger as _get_task_logger, get_logger as _get_logger


class TaskLogFormatter(logging.Formatter):

    DEFAULT_PROPERTIES = set(logging.LogRecord(
        '', '', '', '', '', '', '', '').__dict__.keys())

    def format(self, record):
        """Formats LogRecord into python dictionary."""
        # Standard document
        data = {
            'created': datetime.now(),
            'level': record.levelname,
            'message': record.getMessage(),
        }
        # Standard document decorated with exception info
        if record.exc_info is not None:
            et = record.exc_info[0]
            data.update({
                'exception': {
                    'type': '%s.%s' % (et.__module__, et.__name__),
                    'message': str(record.exc_info[1]),
                    'trace': self.formatException(record.exc_info)
                }
            })
        # Standard document decorated with extra contextual information
        if len(self.DEFAULT_PROPERTIES) != len(record.__dict__):
            contextual_extra = set(record.__dict__).difference(self.DEFAULT_PROPERTIES)
            if contextual_extra:
                for key in contextual_extra:
                    data[key] = record.__dict__[key]

        data.pop('url', None)
        data.pop('task_info', None)
        return data


class TaskLogHandler(logging.Handler):

    def __init__(self, task_name, level=logging.INFO, **kwargs):
        logging.Handler.__init__(self, level)

        self._source = task_name
        self._kwargs = kwargs
        self.setFormatter(TaskLogFormatter())

    @cached_property
    def _save_log(self):
        from celery import current_app
        return current_app.tasks['xspider.save_log']

    def emit(self, record):
        try:
            data = self.format(record)
            if not data:
                return
            self._save_log.apply_async(('log', self._source, data), self._kwargs)
            # self.buffers.clear()
        except Exception:
            self.handleError(record)
        return


class Logger(logging.Logger):

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        record = super(Logger, self).makeRecord(name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)
        if extra and 'local_only' in extra:
            return record

        record_dict = record.__dict__
        meta = record_dict.setdefault('meta', {})
        task = get_current_task()

        if task and task.request and hasattr(task, 'brief'):
            if 'project' not in meta:
                meta.update(task.brief())
            rq = task.request
            meta.update(worker=rq.hostname)
            meta.pop('task_id', None)
            meta.pop('task_name', None)
            record_dict.update(task_id=rq.id, task_name=task.name)
        else:
            record_dict['task_id'] = meta.pop('task_id', '??')
            record_dict['task_name'] = meta.pop('task_name', '??')

        if meta:
            task_info = []
            if 'job' in meta:
                task_info.append('[%s/%s/%s]' % (meta['project'], meta['job'], meta.get('page', '??')))

            if 'action' in meta:
                task_info.append('[%s/%s]' % (meta['project'], meta['action']))

            if 'batch_id' in meta:
                task_info.append('[%s]' % (meta['batch_id'], ))

            record_dict.update({'task_info': ''.join(task_info)})
        else:
            record_dict.setdefault('task_info', '')

        return record


def setup_logger():
    logging.setLoggerClass(Logger)
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def get_task_logger(name, **kw):
    logger = _get_task_logger(name)
    if kw.get('save'):
        h = TaskLogHandler(name)
        logger.addHandler(h)
    return logger


def get_logger(name, **kw):
    logger = _get_logger(name)
    # h = BufferHandler(capped=True, **kw)
    # logger.addHandler(h)
    return logger


