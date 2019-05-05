# coding=utf8

# import sys
# import types
# import six
# from datetime import datetime, timedelta
# from celery.utils.log import logger
from bson.objectid import ObjectId
from xspider.app import app
# from yunduo.errors import ScriptError
from yunduo.resource import get_connection
# from yunduo.dupefilter import Dupefilter
# from yunduo.extractor import Link
# from yunduo.code import get_function
from .base import BaseTask


class SaveLogTask(BaseTask):

    def initialize(self):
        super(SaveLogTask, self).initialize()
        # self.logger = get_task_logger(self.name)
        pagedb = get_connection('page')
        logdb = get_connection('log')
        taskdb = get_connection('task')
        self._task_coll = taskdb['task_infos']
        self._page_coll = pagedb['page_infos']
        self._log_coll = logdb['task_logs']
        self._log_coll.create_index([('created', -1), ('task_id', 1)])
        self._page_coll.create_index([('task_id', 1)])
        self._task_coll.create_index([('received', -1), ('task_id', 1)])

    def _save_task_info(self, tasks, **kw):
        for task_id in tasks:
            # print 'save_task_info %s %s %s' % (task_id, type(buffers), type(task_id))
            data = tasks[task_id]
            if data:
                d1 = {}
                d2 = {}
                dd = {
                    '$push': d1,
                    '$set': d2
                }
                for key in data:
                    if isinstance(data[key], (tuple, list)):
                        d1[key] = data[key]
                    else:
                        d2[key] = data[key]
                if not d1:
                    dd.pop('$push', None)
                if not d2:
                    dd.pop('$set', None)

                if dd:
                    self._task_coll.update_one({'task_id': task_id}, dd, True)

    def _save_page_info(self, page, **kw):
        if isinstance(page, (tuple, list)):
            self._page_coll.insert_many(page)
        else:
            self._page_coll.insert_one(page)

    def _save_log(self, logs, **kw):
        if isinstance(logs, (tuple, list)):
            self._log_coll.insert_many(logs)
        else:
            self._log_coll.insert_one(logs)


@app.task(bind=True, base=SaveLogTask, ignore_result=True, name='xspider.save_log')
def save_log(self, type_, source, data, **kwargs):
    try:
        if type_ == 'task':
            self._save_task_info(data, **kwargs)
        elif type_ == 'page':
            self._save_page_info(data, **kwargs)
        elif type_ == 'log':
            self._save_log(data, **kwargs)
        else:
            self.logger.info('invalid log type %s / %s / %s', type_, source, data)
    except Exception:
        self.logger.exception('save log kwargs=%s', kwargs)
        raise self.retry()

    # task_id = kwargs.pop('task_id', None)
    # extra = {}
    # if task_id:
    #     extra['task_id'] = task_id
    #
    # try:
    #     if script:
    #         num = self.script_save_result(script, data, kwargs)
    #     else:
    #         num = self.default_save_result(data, kwargs)
    #     self.logger.info('Save item, size=%s', num)
    # except Exception:
    #     self.logger.exception('save item kwargs=%s', kwargs)

