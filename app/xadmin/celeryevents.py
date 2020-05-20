# coding=utf8
import time
import atexit
from threading import Thread
from kombu import Consumer
from kombu.entity import Exchange, Queue
from kombu.mixins import ConsumerMixin
from xspider.app import app as celery_app
from xspider.jobaction import JobAction
from xadmin.constant import STATUS_STOP, STATUS_PAUSE, STATUS_START
from xadmin.model.job import Job


class Worker(ConsumerMixin):
    task_queue = Queue('xadmin-notify', Exchange(name='xnotify', type='fanout'), routing_key='xnotify')

    def __init__(self, app):
        self._app = app
        self.logger = app.logger
        self.connection = celery_app.connection_for_read()

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[self.task_queue],
                         callbacks=[self.on_event])]

    def on_event(self, body, message):
        # print('Got task: {0!r}'.format(body))
        # type_, data = json.loads(body)
        type_, data = body
        if type_.startswith('job-'):
            self._on_job(type_, data)
        message.ack()

    def _on_job(self, type_, data):
        self.logger.info('Received: %s - %s', type_, data)
        obj = Job.objects.filter(alias=data['job']).first()
        # print('Job =>', obj)
        if obj.last_batch_id != data['batch_id']:
            # print('!!last_batch_id==', obj.last_batch_id)
            if obj.type == 0:
                return
            elif obj.type == 1:
                obj.last_batch_id = data['batch_id']

        job = JobAction(obj.project.alias, obj.alias, obj.last_batch_id)
        if type_ == 'job-finished':  # job-finished
            r = job.stop()
            obj.status = obj.status & 0xf0 | STATUS_STOP
        elif type_ == 'job-pause':
            r = job.pause()
            obj.status = obj.status & 0xf0 | STATUS_PAUSE
        elif type_ == 'job-started':
            if obj.type == 0:
                return
            elif obj.type == 1:
                obj.status = obj.status & 0xf0 | STATUS_START
        obj.save()

    def stop(self):
        self.should_stop = True


def celery_events(flask_app):
    worker = Worker(flask_app)

    def run():
        with flask_app.app_context():
            worker.run()

    thread = Thread(target=run)
    thread.setDaemon(True)
    thread.start()

    atexit.register(worker.stop)
