# coding=utf8

import json
from datetime import datetime
from celery.utils.saferepr import saferepr
# from celery.utils.log import get_task_logger
from celery import Task, current_app
from xspider.log import get_task_logger
from yunduo.downloader.models import Response


class BaseTask(Task):

    acks_late = True
    resultrepr_maxsize = 128

    def __init__(self):
        super(BaseTask, self).__init__()
        self.initialize()

    def initialize(self):
        self.logger = get_task_logger(self.name)

    def brief(self):
        return {}
    # def shadow_name(self, args, kwargs, options):
    #     return "%s:%s" % (self.name, args[0])

    # def after_return(self, status, retval, task_id, args, kwargs, einfo):
    #     pass

    def send_task(self, task_name, args=None, kwargs=None, task_id=None, producer=None,
                  link=None, link_error=None, shadow=None, **options):
        app = self._get_app()
        try:
            task = app.tasks[task_name]
        except KeyError:
            task = app.tasks['xspider.%s' % task_name]

        task.apply_async(args, kwargs, task_id, producer, link, link_error, shadow, **options)

    # def pause(self):
    #     self._get_app().control.cancel_consumer(self.queue, reply=True)


class StrategyTask(BaseTask):
    # 定义自己的策略
    Strategy = 'xspider.strategy:default'

    # rate_limit = False
    # counter = False
    # store_info = False
    # custom_queue = False
    # _exchange = None

    def initialize(self):
        # self._exchange = None
        self.logger = get_task_logger(self.name, save=True)

    def brief(self, args=None, kwargs=None):
        return {}

    def send_message(self, data, type_='message', **kw):
        info = self.brief()
        exchange = kw.get('exchange', 'xmessage')
        routing_key = kw.get('routing_key', 'xmessage')

        self.logger.info(u'Notify %s <%s %s>' % (saferepr(data, 128), exchange, routing_key))

        if not isinstance(data, dict):
            data = {
                'data': data
            }

        data.update(info)

        current_app.send_message(type_, data, exchange, routing_key)
        save_kw = {}
        save_dt = ('task', self.name, {self.request.id: {'message': [data]}})
        self.send_task('xspider.save_log', save_dt, save_kw)

    def save_page(self, resp, **kwargs):
        try:
            info = self.brief()
            if isinstance(resp, Response):
                data = resp.to_dict()
            else:
                data = resp
            if 'cookies' in data:
                data['cookies'] = json.dumps(data['cookies'])

            req = self.request
            data['task_id'] = req.id
            info['task_id'] = req.id
            info['task_name'] = self.name
            info['worker'] = req.hostname
            data['meta'] = info
            data['created'] = datetime.now()
            self.send_task('save_log', ('page', self.name, data), {})
        except Exception:
            self.logger.exception(u'保存Response出错')

    def signature_from_request(self, request=None, args=None, kwargs=None,
                               queue=None, **extra_options):
        if request.delivery_info:
            request.delivery_info.pop('exchange', None)
            request.delivery_info.pop('routing_key', None)

        return super(StrategyTask, self).signature_from_request(request, args, kwargs, queue, **extra_options)

    # def counter_key(self, args, kwargs):
    #     return self.name, ''

    # def on_all_finished(self, *args, **kwargs):
    #     pass

    # def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
    #                 link=None, link_error=None, shadow=None, **options):
    #     # if self.custom_queue:
    #     #     app = self._get_app()
    #     #     batch_id = kwargs and kwargs.get('batch_id')
    #     #     qname = app.get_queue_name(args[0], batch_id)
    #     #     options['queue'] = Queue(qname, exchange=self._exchange, routing_key=batch_id)
    #     return super(StrategyTask, self).apply_async(args, kwargs, task_id, producer,
    #                                                  link, link_error, shadow, **options)

    # def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
    #                 link=None, link_error=None, shadow=None, **options):
    #     if kwargs:
    #         cq = kwargs.get('__queue__')
    #         if cq and len(cq) == 3:
    #             options['queue'] = Queue(cq[0], Exchange(cq[1], type='direct'), cq[2])
    #     return super(StrategyTask, self).apply_async(args, kwargs, task_id, producer,
    #                                                  link, link_error, shadow, **options)

