# coding=utf8

from celery.utils.saferepr import saferepr
from yunduo.utils import gen_id, md5sum
from yunduo.resource import get_connection
from xspider.app import app
from xspider.jobaction import JobAction, ActionAction
from .base import BaseTask


class BeatTask(BaseTask):

    def initialize(self):
        super(BeatTask, self).initialize()
        self.redis_run = get_connection('run')


@app.task(bind=True, base=BeatTask, ignore_result=True, name='xspider.beat')
def beat(self, task, args, kwargs, **kw):
    key = '%s:%s' % (task, md5sum((args, kwargs)))
    last = self.redis_run.hget('beat:running', key)
    if task == 'crawl':
        meta = {
            'project': args[0],
            'job': args[1],
            'page': args[2],
            'url': args[3],
            'batch_id': last
        }
        ja = None
        if last:
            ja = JobAction(args[0], args[1], last)
        if ja and ja.is_running():
            self.logger.warn('任务 %s / %s 正在运行中 %s %s', task, last, saferepr(args, 128),
                             saferepr(kwargs, 128), extra={'meta': meta})
            return

        batch_id = gen_id('btj')
        ja = JobAction(args[0], args[1], batch_id)
        t = ja.start(kwargs)
        self.redis_run.hset('beat:running', key, batch_id)
        meta['batch_id'] = batch_id
        self.logger.info('运行任务 %s(%s %s) / %s', task, saferepr(args, 128), saferepr(kwargs, 128),
                         ja.id, extra={'meta': meta})
    elif task == 'action':
        if last:
            self.logger.warn('任务 %s / %s 正在运行中 %s %s', task, last, saferepr(args, 128), saferepr(kwargs, 128))
            return
        batch_id = gen_id('bta')
        ja = ActionAction(args[0], args[1], batch_id)
        t = ja.start(kwargs, link=beat_finished.si(key), link_error=beat_finished.si(key))
        self.redis_run.hset('beat:running', key, batch_id)
        self.logger.info('运行任务 %s(%s %s) / %s', task, saferepr(args, 128), saferepr(kwargs, 128), ja.id)
    else:
        if last:
            self.logger.warn('任务 %s / %s 正在运行中 %s %s', task, last, saferepr(args, 128), saferepr(kwargs, 128))
        else:
            t = self.send_task(task, args, kwargs, link=beat_finished.si(key), link_error=beat_finished.si(key))
            self.redis_run.hset('beat:running', key, '1')
            self.logger.info('运行任务 %s(%s %s) / %s', task, saferepr(args, 128), saferepr(kwargs, 128), t and t.id)


@app.task(bind=True, base=BeatTask, ignore_result=True, name='xspider.beat_finished')
def beat_finished(self, key):
    self.redis_run.hdel('beat:running', key)
    self.logger.info('DONE %s', key)
