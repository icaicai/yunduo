# coding=utf8

import sys
import types
import six
from datetime import datetime, timedelta
from w3lib.url import parse_url
from celery.utils.log import logger
from yunduo.errors import ScriptError
from yunduo.resource import get_connection
from yunduo.dupefilter import Dupefilter
from yunduo.parser.htmlextractor import Link
from yunduo.code import get_function
from xspider.log import get_task_logger
from xspider.app import app
from .base import BaseTask


class SaveResultTask(BaseTask):

    def initialize(self):
        # super(SaveResultTask, self).initialize()
        # self.logger = get_task_logger(self.name)
        self.logger = get_task_logger(self.name, save=True)
        self.df = Dupefilter()
        self.influx_stat = get_connection('stat')

    # def save_task_info(self, buffers, **kw):
    #     col_task = self.get_collection('task', **kw)
    #     for task_id in buffers:
    #         # print 'save_task_info %s %s %s' % (task_id, type(buffers), type(task_id))
    #         data = buffers[task_id]
    #         if data:
    #             d1 = {}
    #             d2 = {}
    #             for key in data:
    #                 if isinstance(data[key], (tuple, list)):
    #                     d1[key] = data[key]
    #                 else:
    #                     d2[key] = data[key]
    #             if d1:
    #                 col_task.update_one({'_id': task_id}, {'$pushAll': d1}, True)
    #             if d2:
    #                 col_task.update_one({'_id': task_id}, {'$set': d2}, True)

    def report_stat(self, **kw):
        req = self.request
        worker = req.hostname
        args = req.args
        kwargs = req.kwargs
        host = kwargs.pop('hostname', '')
        url = kwargs.pop('url', '')
        if not host and url:
            try:
                host = parse_url(url).hostname
            except Exception:
                host = ''
        fields = kw

        data = {
            "measurement": "save_stat",
            "tags": {
                "project": kwargs['project'],
                "job": kwargs['job'],
                "page": kwargs['page'],
                "host": host,
                "worker": worker,
                "batch_id": kwargs.get('batch_id')
            },
            "time": datetime.now(),
            "fields": fields
        }

        # self.logger.info(u'统计回报 %s', data)
        try:
            self.influx_stat.write_points([data])
        except Exception:
            self.logger.exception('统计回报异常')

    def script_save_result(self, script, data, kwargs):
        batch_id = kwargs.get('batch_id')
        task_id = kwargs.get('task_id', None)
        task_name = kwargs.get('task_name', None)
        task_kwargs = kwargs.get('kwargs', None)

        extra = {}
        if task_id:
            extra['task_id'] = task_id
        if task_name:
            extra['task_name'] = task_name
        if batch_id:
            extra['batch_id'] = batch_id

        def _crawl(page, url=None, project=None, job=None, **kw):
            if isinstance(page, Link):
                lnk = page
            else:
                lnk = Link(page, url, **kw)

            project = project or kwargs.get('project')
            job = job or kwargs.get('job')

            if not project or not job or not page:
                return False

            if not self.df.seen(project, job, lnk):
                return False

            if task_kwargs:
                dkw = task_kwargs.copy()
            else:
                dkw = {}
            dkw['lconf'] = lnk.conf
            dkw.setdefault('batch_id', batch_id)
            self.send_task('crawl', (project, job, lnk.page, lnk.url), dkw)

        env = {
            # 'send_notify': _send_notify,
            'get_connection': get_connection,
            'Link': Link,
            'crawl': _crawl,
            'dprint': lambda *args, **kw: None,
            'environ': kwargs
        }

        func = get_function(script, env)
        if func:
            num = func(data)
            if num is None:
                if isinstance(data, dict):
                    num = 1
                else:
                    num = len(data)
            return num
        else:
            raise ScriptError(u'找不到执行入口 %s', script)

    def default_save_result(self, data, kwargs):
        project = kwargs['project']
        page = kwargs['page']
        _meta = {
            'project': project,
            'job': kwargs.get('job'),
            'page': page,
            'batch_id': kwargs.get('batch_id'),
            'created': kwargs.get('created', datetime.now()),
        }

        db = get_connection('result')
        col = db['%s_%s' % (project, page)]
        if isinstance(data, dict):
            data['_meta'] = _meta
            col.insert_one(data)
            return 1
        else:
            for it in data:
                it['_meta'] = _meta
            col.insert_many(data)
            return len(data)


@app.task(bind=True, base=SaveResultTask, ignore_result=True, name='xspider.save_result')
def save_result(self, script, data, **kwargs):
    meta = {}
    for key in ('project', 'job', 'page', 'url', 'batch_id', 'task_id', 'task_name'):
        if key in kwargs:
            meta[key] = kwargs[key]

    try:
        if script:
            num = self.script_save_result(script, data, kwargs)
        else:
            num = self.default_save_result(data, kwargs)
        self.logger.info('成功保存了 %s 条记录', num, extra={'meta': meta})
        self.report_stat(save_num=num)
    except Exception:
        self.logger.exception('保存异常 kwargs=%s', kwargs, extra={'meta': meta})
        self.report_stat(save_exc=1)


