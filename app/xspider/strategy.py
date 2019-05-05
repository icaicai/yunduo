# -*- coding: utf-8 -*-
"""Task execution strategy (optimization)."""
from __future__ import absolute_import, unicode_literals
import time
import logging
from kombu.utils import json
from datetime import datetime, timedelta
from kombu.asynchronous.timer import to_timestamp
from kombu.five import buffer_t

from weakref import ref
from celery.result import AsyncResult
from celery.worker import state
from celery.app.trace import trace_task_ret

from celery.exceptions import InvalidTaskError, TaskRevokedError
# from celery.utils.log import get_logger
# from celery.utils.saferepr import saferepr
from celery.utils.time import timezone, maybe_make_aware
from celery.utils.functional import maybe
from celery.worker.request import Request  # , create_request_cls
from celery.worker.state import task_reserved

from yunduo.resource import get_connection
from yunduo.rate import get_expected_time
from xspider.log import get_logger, get_task_logger
# from xspider.taskstore import TaskStore

__all__ = ['default']

logger = get_logger(__name__)

# pylint: disable=redefined-outer-name
# We cache globals and attribute lookups, so disable this warning.


def default(task, app, consumer,
            info=logger.info, error=logger.error, task_reserved=task_reserved,
            to_system_tz=timezone.to_system, bytes=bytes, buffer_t=buffer_t):
    """Default task execution strategy.

    Note:
        Strategies are here as an optimization, so sadly
        it's not very easy to override.
    """
    redis_run = get_connection('run')

    hostname = consumer.hostname
    connection_errors = consumer.connection_errors
    _does_info = logger.isEnabledFor(logging.INFO)

    # task event related
    # (optimized to avoid calling request.send_event)
    eventer = consumer.event_dispatcher
    events = eventer and eventer.enabled
    send_event = eventer.send
    task_sends_events = events and task.send_events

    call_at = consumer.timer.call_at
    apply_eta_task = consumer.apply_eta_task
    rate_limits_enabled = not consumer.disable_rate_limits
    get_bucket = consumer.task_buckets.__getitem__
    handle = consumer.on_task_request
    limit_task = consumer._limit_task
    body_can_be_buffer = consumer.pool.body_can_be_buffer

    # Req = create_request_cls(Request, task, consumer.pool, hostname, eventer)
    # def create_request_cls(base, task, pool, hostname, eventer,
    #                        ref=ref, revoked_tasks=revoked_tasks,
    #                        task_ready=task_ready, trace=trace_task_ret):
    # default_time_limit = task.time_limit
    # default_soft_time_limit = task.soft_time_limit
    # apply_async = pool.apply_async
    # acks_late = task.acks_late
    # events = eventer and eventer.enabled
    # task_ready = state.task_ready
    # task_accepted = state.task_accepted
    task_ready = state.task_ready
    revoked_tasks = state.revoked

    default_time_limit = task.time_limit
    default_soft_time_limit = task.soft_time_limit
    apply_async = consumer.pool.apply_async
    # print '=======-----', consumer, consumer.pool, apply_async
    acks_late = task.acks_late
    events = eventer and eventer.enabled
    # == END == Request var

    controller_revoked_tasks = consumer.controller.state.revoked

    task_name = task.name
    # celery_app = task._get_app()
    # task_send_task = task.send_task
    # log_exception = task.logger.exception
    # _logger = get_task_logger(task_name, save=True)
    # _info = _logger.info
    # _error = _logger.error
    _info = task.logger.info
    _error = task.logger.error

    # task_store_info = task.store_info
    # task_rate_limit = task.rate_limit
    # task_counter = task.counter
    get_task_info = task.brief
    # task_counter_key = task.counter_key
    # task_on_all_finished = task.on_all_finished

    # taskstore = TaskStore(task_name)

    task_save = app.tasks['xspider.save_log']

    def save_task_status(type_, task_id, data):
        type_, _, subject = type_.partition('-')
        if type_ != 'task' or not data:
            return

        data[subject] = datetime.now()
        data['task_id'] = task_id
        task_save.apply_async(('task', task_name, {task_id: data}))

    # dispatcher = consumer.event_dispatcher
    # if dispatcher.groups and 'project' not in dispatcher.groups:
    #     dispatcher.groups.add('project')
    #     info('Events of group {project} enabled by local.')

    class BaseReq(Request):
        def __init__(self, *args, **kwargs):
            super(BaseReq, self).__init__(*args, **kwargs)
            self._args, self._kwargs, self._embed = self._payload

        def execute_using_pool(self, pool, **kwargs):
            task_id = self.id
            if (self.expires or task_id in revoked_tasks) and self.revoked():
                raise TaskRevokedError(task_id)

            time_limit, soft_time_limit = self.time_limits
            result = pool.apply_async(
                trace_task_ret,
                args=(self.type, task_id, self.request_dict, self.body,
                      self.content_type, self.content_encoding),
                accept_callback=self.on_accepted,
                timeout_callback=self.on_timeout,
                callback=self.on_success,
                error_callback=self.on_failure,
                soft_timeout=soft_time_limit or default_soft_time_limit,
                timeout=time_limit or default_time_limit,
                correlation_id=task_id,
            )
            # cannot create weakref to None
            # pylint: disable=attribute-defined-outside-init
            self._apply_result = maybe(ref, result)
            return result

        def on_success(self, failed__retval__runtime, **kwargs):
            failed, retval, runtime = failed__retval__runtime
            if failed:
                if isinstance(retval.exception, (
                        SystemExit, KeyboardInterrupt)):
                    raise retval.exception
                return self.on_failure(retval, return_ok=True)
            task_ready(self)

            if acks_late:
                self.acknowledge()

            if events:
                self.send_event(
                    'task-succeeded', result=retval, runtime=runtime,
                )

        def send_event(self, type_, **fields):
            super(BaseReq, self).send_event(type_, **fields)
            if type_ == 'task-succeeded':
                try:
                    if 'result' in fields:
                        fields['result'] = json.dumps(fields['result'])
                except Exception:
                    pass
            # taskstore.save(type_, self.id, fields)
            save_task_status(type_, self.id, fields)

        def task_info(self):
            info = get_task_info(self._args, self._kwargs)
            info['task_id'] = self.id
            info['task_name'] = task_name
            info['worker'] = self.hostname
            return info

    def task_message_handler(message, body, ack, reject, callbacks, to_timestamp=to_timestamp):
        # print('crawl_task_message_handler %s %s' % (task_name, repr(body)))
        body, headers, decoded, utc = (message.body, message.headers, False, True,)
        if not body_can_be_buffer:
            body = bytes(body) if isinstance(body, buffer_t) else body

        req = BaseReq(
            message,
            on_ack=ack, on_reject=reject, app=app, hostname=hostname,
            eventer=eventer, task=task, connection_errors=connection_errors,
            body=body, headers=headers, decoded=decoded, utc=utc,
        )
        # if _does_info:
        meta = req.task_info()
        taskinfo = {'meta': meta}
        _info(u'收到任务', extra=taskinfo)

        if (req.expires or req.id in controller_revoked_tasks) and req.revoked():
            return

        # req_args, req_kwargs, req_embed = req._payload
        if task_sends_events:
            send_event(
                'task-received',
                uuid=req.id, name=req.name,
                args=req.argsrepr, kwargs=req.kwargsrepr,
                root_id=req.root_id, parent_id=req.parent_id,
                retries=req.request_dict.get('retries', 0),
                eta=req.eta and req.eta.isoformat(),
                expires=req.expires and req.expires.isoformat(),
            )

        # 保存
        # ti = get_task_info(req._args, req._kwargs)
        fields = dict(
            name=req.name,
            # project=req._project, page=req._page, url=req._url,
            kwargs=json.dumps(req._kwargs),
            # args=req_args, kwargs=req_kwargs,
            root_id=req.root_id, parent_id=req.parent_id,
            retries=req.request_dict.get('retries', 0),
            eta=req.eta and req.eta.isoformat(),
            expires=req.expires and req.expires.isoformat(),
            meta=meta
        )
        save_task_status('task-received', req.id, fields)

        # 限速
        if req._kwargs.get('__limit__'):
            try:
                key = 'rate:%s' % meta['project']
                pending = get_expected_time(key)
                # print '----Rate limit pending: %s %r' % (req.id, pending)
                if pending > 0:
                    req.eta = maybe_make_aware(datetime.utcnow() + timedelta(seconds=pending))
                    info('Rate Limit [%s.%s] %s', meta['project'], meta['page'], pending)
            except Exception:
                error('Rate limit. Task: %r', req.info(safe=True), exc_info=True)

        if req.eta:
            try:
                if req.utc:
                    eta = to_timestamp(to_system_tz(req.eta))
                else:
                    eta = to_timestamp(req.eta, timezone.local)
            except (OverflowError, ValueError):
                error("Couldn't convert ETA %r to timestamp. Task: %r",
                      req.eta, req.info(safe=True), exc_info=True)
                req.reject(requeue=False)
            else:
                consumer.qos.increment_eventually()
                call_at(eta, apply_eta_task, (req,), priority=6)
        else:
            if rate_limits_enabled:
                bucket = get_bucket(task.name)
                if bucket:
                    return limit_task(req, bucket, 1)
            task_reserved(req)
            if callbacks:
                [callback(req) for callback in callbacks]
            handle(req)

    return task_message_handler
