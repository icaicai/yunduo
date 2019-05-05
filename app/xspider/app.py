
import json

from kombu.utils.objects import cached_property
from kombu.entity import Exchange, Queue
from celery.utils.saferepr import saferepr
from celery.utils.encoding import bytes_to_str
from celery.signals import worker_ready
from celery.utils.log import get_logger
from celery import Celery

logger = get_logger('xspider')


class App(Celery):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('control', 'xspider.control:Control')
        # kwargs.setdefault('log', 'xspider.log:Logging')
        kwargs.setdefault('config_source', 'conf.xspider')
        kwargs.setdefault('include', ['xspider.tasks'])
        super(App, self).__init__(*args, **kwargs)

    def init_queue(self):
        Queue.from_dict('xmessage', exchange='xmessage')
        self._exchage = Exchange('xnofity', type='fanout')

    @cached_property
    def channel(self):
        conn = self.connection_for_write().clone()
        return conn.default_channel

    @cached_property
    def xnotify_exchange(self):
        ex = Exchange('xnofity', type='fanout', channel=self.channel)
        ex.declare()
        return ex

    def send_message(self, type_, data, exchange, routing_key, **kw):
        with self.connection_or_acquire() as conn:
            data = json.dumps((type_, data))
            channel = conn.default_channel
            msg = channel.prepare_message(data, content_type='application/json')
            return channel.basic_publish(msg, exchange=exchange, routing_key=routing_key)

    def send_notify(self, channel, data, **kw):
        try:
            with self.connection_or_acquire() as conn:
                data = json.dumps((channel, data))
                channel = conn.default_channel
                msg = channel.prepare_message(data, content_type='application/json')
                return channel.basic_publish(msg, exchange='xnotify', routing_key='xnotify', **kw)
        except:
            logger.exception('send notify error %s / %s ', channel, saferepr(data, 128))

app = App()


# @app.on_after_configure.connect
# def on_configured(sender, source, **kwargs):
#     if source['beat_key_prefix']:
#         source['beat_schedule_key'] = source['beat_key_prefix'] + ':schedule'

# @app.on_after_setup_logger.connect
# def on_setup_logger(sender=None, logger=root, loglevel=loglevel, logfile=logfile,
#     format=format, colorize=colorize):
#     import logging
#     formatter = logger.handlers[0].formatter
#     handler = logging.StreamHandler(logfile)
#     handler.setFormatter(formatter(format, use_color=colorize))
#     logger.addHandler(handler)
#     return logger


@worker_ready.connect
def on_worker_ready(sender, signal, **kwargs):
    # redis_conf = redis.from_url(app.conf.redis['conf'])
    from yunduo.resource import get_connection

    redis_run = get_connection('run')
    kw = {
        'exchange': 'xcrawl',
        'reply': True,
        'binding_key': None,
        'exchange_type': 'direct',
        'queue_arguments': {'x-max-priority': 10},
        'consumer_arguments': {'x-priority': 8}
    }
    # for p, s in redis_run.zscan_iter('queue:running'):
    running = redis_run.hgetall('queue:running')
    for q, s in running.items():
        if bytes_to_str(s) == 'pause':
            continue
        logger.info('regain consuming %s %s', q, s)
        q1 = bytes_to_str(q)
        kkw = kw.copy()
        kkw['binding_key'] = q1.split(':')[3]
        sender.add_task_queue(q1, **kw)

    # print '----------on_worker_ready------------'
    # dispatcher = sender.event_dispatcher
    # if dispatcher.groups and 'task' not in dispatcher.groups:
    #     dispatcher.groups.add('task')
    #     logger.info('Events of group {task} enabled by local.')
