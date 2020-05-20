# coding=utf8

import time
import json
from datetime import datetime
from celery.schedules import schedule, crontab
from flask import current_app, flash, jsonify
from jinja2 import Markup
from flask_mongoengine.wtf import fields
from flask_admin import expose
from flask_admin.actions import action
from flask_admin.form import rules
from flask_admin.model.template import TemplateLinkRowAction
from xadmin.view.base import BaseView
from xadmin.base.rules import Row, Column
from xadmin.utils.format import date_format, map_format, edit_link_format
from xadmin.constant import STATUS_STOP, STATUS_PAUSE, STATUS_START, STATUS_PUBLISH
from yunduo.conf import xconf
from yunduo.rate import parse_rate
from yunduo.resource import get_connection
from yunduo.dupefilter import Dupefilter
from xspider.jobaction import JobAction


class EntryRowAction(TemplateLinkRowAction):
    def __init__(self):
        super(EntryRowAction, self).__init__(
            'row_actions.job_action_row',
            u'')


def status_format(view, context, model, name):
    names = {STATUS_START: u'启用', STATUS_PAUSE: u'暂停', STATUS_STOP: u'停用', STATUS_PUBLISH: '已发布'}
    s = []
    val = getattr(model, name, 0)
    if val & 0xf0 == STATUS_PUBLISH:
        s.append('已发布')
    b = val & 0x0f
    s.append(names.get(b))
    return ' / '.join(s)


# Customized admin views
class JobView(BaseView):
    inject_current_project = True
    list_template = 'admin/model/job_list.html'
    edit_template = 'admin/model/job_edit.html'
    create_template = 'admin/model/job_create.html'

    column_extra_row_actions = [EntryRowAction()]

    column_list = ['name', 'alias', 'status', 'priority', 'type', 'proxy_type', 'last_batch.batch_id', 'updated']
    column_filters = ['name', 'alias']

    column_labels = {
        'project': u'所属项目',
        'name': u'名称',
        'alias': u'别名',
        'entry_type': u'入口类型',
        'entry_page': u'入口页面',
        'entry_script': u'入口脚本',
        'type': u'类型',
        'status': u'状态',
        'entry_url': u'入口URL',
        'tags': u'标签',
        'schedule': u'调度周期',
        'schedule_type': u'调度类型',
        'priority': u'优先级',
        'rate_limit': u'限速',
        'incr_mode': '增量模式',
        'max_retries': u'重试次数',
        'proxy_type': u'代理策略',
        'df_expire': u'去重过期',
        'df_query_only': 'URL参数保留',
        'df_query_remove': 'URL参数移除',
        'headers': u'HTTP头',
        'http_valid_code': '有效状态码',
        'http_retry_code': '重试状态码',

        'last_batch.batch_id': '最后一次任务ID',

        'save_page': u'页面保存',
        'cookie_type': u'Cookie策略',
        'finish_script': u'抓取完成时',

        'deny_code': u'特征状态码',
        'deny_text': u'特征文本',
        'deny_script': u'脚本检测',
        'deny_retry': u'反爬重试',

        'owner': u'创建人',
        'created': u'新增时间',
        'updated': u'更新时间',
        'published': u'发布时间'
    }

    column_searchable_list = ('name', 'alias')
    column_formatters = {
        'name': edit_link_format,
        'status':status_format,
        'type': map_format({0: u'普通', 1: '调度', 2: u'授权'}),
        'save_page': map_format({0: u'不保存', 1: u'解析失败时', 2: u'所有页面'}),
        'proxy_type': map_format({0: u'不使用', 1: u'即时', 2: u'持久'}),
        'cookie_type': map_format({0: u'不使用', 1: u'即时', 2: u'持久'}),
        'created': date_format,
        'updated': date_format,
        'published': date_format,
    }

    # form_overrides = {
    #     'entry_type': fields.RadioField
    # }

    form_ajax_refs = {
        '__self__': {
            'fields': ('name', 'alias')
        },
        'entry_page': {
            'fields': ('name', 'alias')
        },
        'entry_script': {
            'fields': ('name', 'alias')
        },
        'batches': {
            'model': 'JobBatch',
            'fields': ('batch_id', ),
            'key': 'batch_id',
            'order_by': '+created'
        }
    }

    form_args = {
        'project': {
            'readonly': 'readonly'
        },
        'entry_type': {
            'radio': True
        }
    }

    form_widget_args = {
        'schedule': {
            'prepend': {
                'name': 'schedule_type'
            }
        },
        'entry_page': {
            # 'data-filters': 'project',
            'append': {
                'class': 'input-group-btn',
                # 'content': '<button class="btn btn-info add-page"><i class="fa fa-plus"></i></button>'
                'content': ('<a class="btn btn-primary new-page-simple"'
                            'title="创建新页面" ><i class="fa fa-plus-circle"></i></a>')
            }
        },
        'entry_script': {
            # 'data-filters': 'project',
            'append': {
                'class': 'input-group-btn',
                # 'content': '<button class="btn btn-info add-page"><i class="fa fa-plus"></i></button>'
                'content': ('<a class="btn btn-primary new-script-simple"'
                            'title="创建新脚本" ><i class="fa fa-plus-circle"></i></a>')
            }
        },
        'rate_limit': {
            'placeholder': u'"100/5m", "2/h" or "0.5/s"'
        },
        'df_query_only': {
            'placeholder': u'只保留所列出的参数名。每行一个参数名'
        },
        'df_query_remove': {
            'placeholder': u'移除所列出的参数名。每行一个参数名'
        },
        'deny_code': {
            'placeholder': u', \\n'
        },
        'deny_text': {
            'placeholder': u'每行一个特征'
        },
        'deny_script': {
            'data-role': 'editor',
            'data-lang': 'python',
            'data-max-lines': 10
        },
    }

    # form_extra_fields = {'schedule_type': 'schedule_type'}
    form_rules = [
        'project',
        Row(Column('name', 'alias', 'entry_type', 'entry_url', 'entry_page', 'entry_script',
                   'incr_mode', 'http_valid_code'),
            Column('type', 'schedule', 'rate_limit', 'max_retries',
                   'save_page', 'proxy_type', 'cookie_type', 'http_retry_code')),
        rules.Header(u'URL去重/参数清理设置', 'lib.form_header'),
        'df_expire', 'df_query_only', 'df_query_remove',

        rules.Header(u'反爬特征检测', 'lib.form_header'),
        'deny_code', 'deny_text', 'deny_script'
        # 'periodic', 'http_retry_code'
    ]

    # form_widget_args = {
    #     'blocked_code': {
    #         'placeholder': u'每行一个特征'
    #     },
    #     'blocked_text': {
    #         'placeholder': u'每行一个特征'
    #     }
    # }

    # def _get_job(self, id):
    #     obj = self.get_one(id)
    #     job = JobAction(obj.project.alias, obj.alias, obj.last_batch_id)
    #     return job
    #
    # def _set_status(self, job, status):
    #     job.status = status
    #     job.save()

    # def _refresh_forms_cache(self):
    #     from wtforms.fields import HiddenField
    #     from wtforms.validators import InputRequired
    #     super(JobView, self)._refresh_forms_cache()
    #
    #     class ActionForm(self.form_base_class):
    #         id = HiddenField()
    #         act = HiddenField()
    #         url = HiddenField()
    #
    #     self._a_form_class = ActionForm
    #
    # def action(self):
    #     form = self.delete_form()
    #     id = form.id.data

    def on_model_change(self, form, model, is_created):
        if model.type == 2:
            model.cookie_type = '__t__'
        super(JobView, self).on_model_change(form, model, is_created)

    @expose('/status/<string:id>')
    def status(self, id):
        obj = self.get_one(id)
        job = JobAction(obj.project.alias, obj.alias, obj.last_batch_id)
        q = job.status()
        return jsonify(q)

    @expose('/pause/<string:id>', methods=('GET', ))
    def pause(self, id):
        obj = self.get_one(id)
        if not obj.last_batch_id:
            return jsonify({'success': False, 'message': '任务没有启动'})

        job = JobAction(obj.project.alias, obj.alias, obj.last_batch_id)
        r = job.pause()
        r = True
        if r:
            obj.status = STATUS_PAUSE
            obj.save()
        return jsonify({'success': r, 'message': '任务 < %s > 暂停' % obj})

    @expose('/start/<string:id>', methods=('GET', ))
    def start(self, id):
        obj = self.get_one(id)
        job_conf = obj.to_conf()
        xconf.set_job(obj.project.alias, obj.alias, job_conf)
        # if obj.type != 0:
        #     return jsonify({'success': False, 'message': '定时任务'})

        if obj.type == 0:
            if not obj.last_batch or obj.last_batch.is_finished():
                b = obj.new_batch()
                job = JobAction(obj.project.alias, obj.alias, b.batch_id)
                r = job.start()
            else:
                job = JobAction(obj.project.alias, obj.alias, obj.last_batch_id)
                r = job.resume()
        elif obj.type == 1:
            from xbeat import Store
            sch = None
            max_run_count = None
            if obj.schedule_type == 'datetime':
                sch = datetime.strptime(obj.schedule, '%Y-%m-%d %H:%M:%S') - datetime.now()
                max_run_count = 1
            elif obj.schedule_type == 'schedule':
                sch = schedule(float(obj.schedule))
            elif obj.schedule_type == 'crontab':
                args = list(filter(lambda s: s.strip(), obj.schedule.split(' ')))
                sch = crontab(*args)

            if sch:
                if job_conf['entry_type'] == 1:
                    args = (obj.project.alias, obj.alias, job_conf['entry_script'], None)
                else:
                    args = (obj.project.alias, obj.alias, job_conf['entry_page'], job_conf['entry_url'])

                kwargs = {}
                if job_conf['rate_limit']:
                    kwargs['__limit__'] = True
                # name = None, task = None, last_run_at = None,
                # total_run_count = None, schedule = None, args = (), kwargs = {},
                # options = {}, relative = False, app = None
                Store.add({
                    'name': '%s-%s' % (obj.project.alias, obj.alias),
                    'task': 'xspider.beat',
                    'schedule': sch,
                    'args': ('crawl', args, kwargs),
                    'kwargs': {},
                    'max_run_count': max_run_count
                })

        r = True
        if r:
            obj.status = STATUS_START if obj.type == 0 else STATUS_PUBLISH
            obj.save()
        # if obj.type == 0:
        #     job.start()
        #     obj.status = START
        #     obj.save()
        #     current_app.logger.info(u'恢复项目 %s', obj.name, extra={'project': obj.alias})
        #     r = True
        # else:
        #     r = False
        return jsonify({'success': r})

    @expose('/stop/<string:id>', methods=('GET', ))
    def stop(self, id):
        obj = self.get_one(id)
        xconf.del_job(obj.project.alias, obj.alias)
        if obj.type == 0:
            job = JobAction(obj.project.alias, obj.alias, obj.last_batch_id)
            r = job.stop()
        elif obj.type == 1:
            from xbeat import Store
            Store.remove('%s-%s' % (obj.project.alias, obj.alias))

        r = True
        if r:
            obj.status = STATUS_STOP
            if obj.last_batch:
                obj.last_batch.stop()
            obj.save()
        return jsonify({'success': r})

    @expose('/purge/<string:id>', methods=('GET', ))
    def purge(self, id):
        obj = self.get_one(id)
        job = JobAction(obj.project.alias, obj.alias, obj.last_batch_id)
        r = job.purge()
        return jsonify({'success': r})

    @expose('/purgede/<string:id>', methods=('GET', ))
    def purgede(self, id):
        df = Dupefilter()
        obj = self.get_one(id)
        df.delete(obj.project.alias, obj.alias, obj.last_batch_id, tmp=True, incr_mode=obj.incr_mode)
        return jsonify({'success': 1})

    @expose('/publish/<string:id>', methods=('GET', ))
    def publish(self, id):
        obj = self.get_one(id)
        xconf.set_job(obj.project.alias, obj.alias, obj.to_conf())
        return jsonify({'success': 1})
