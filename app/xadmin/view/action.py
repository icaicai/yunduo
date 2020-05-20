# coding=utf8

import json
from datetime import datetime
from flask import current_app, flash
from flask_admin import expose
from flask_admin.actions import action
from flask_admin.helpers import get_form_data
from flask_admin.form import rules
from yunduo.conf import xconf
from xadmin.view.base import BaseView
from xadmin.utils.format import date_format, map_format, edit_link_format
from xadmin.constant import STATUS_DISABLE, STATUS_ENABLE
from xadmin.base.rules import Row, Column
# from connections import redis_conf


# Customized admin views
class ActionView(BaseView):
    inject_current_project = True
    edit_template = 'admin/model/action_edit.html'
    create_template = 'admin/model/action_create.html'

    column_list = ['name', 'alias', 'lang', 'project', 'status', 'updated', 'published']
    # column_filters = ['name', 'alias']

    column_labels = {
        'name': u'名称',
        'alias': u'别名',
        'project': u'所属项目',
        'tags': u'标签',
        'lang': u'代码语言',
        'status': u'状态',
        'timeout': u'超时时间',

        'multistage': '多次交互',

        'jscode': u'Js代码',
        'pycode': u'Py代码',

        'created': u'新增时间',
        'updated': u'更新时间',
        'published': u'发布时间'

    }

    column_searchable_list = ('name', 'alias')
    column_formatters = {
        'name': edit_link_format,
        'status': map_format({STATUS_ENABLE: u'启用', STATUS_DISABLE: u'停用'}),
        'lang': map_format({0: u'Javascript', 1: u'Python'}),
        'created': date_format,
        'updated': date_format,
        'published': date_format,
    }

    form_ajax_refs = {
        '__self__': {
            'fields': ('name', 'alias'),
            'key': 'alias'
        }
    }

    form_args = {
        'project': {
            'readonly': 'readonly'
        },
        'lang': {
            'radio': True
        }
    }

    form_rules = [
        'project',
        Row(Column('name', 'alias'),
            Column('multistage')),
        Row(Column('lang'), Column('timeout')),
        'jscode', 'pycode'
    ]

    form_widget_args = {
        'jscode': {
            'data-role': 'editor',
            'data-lang': 'javascript',
            'data-min-lines': 30
        },
        'pycode': {
            'data-role': 'editor',
            'data-lang': 'python',
            'data-min-lines': 30
        }
    }

    # form_ajax_refs = {
    #     '__self__': {
    #         'fields': ('name',),
    #         'filters': {
    #             'status': STATUS_ENABLE
    #         }
    #     }
    # }

    # form_rules = [
    #     Row(Column('name'), Column('alias')),
    #     Row(Column('category'), Column('project')),
    #     rules.Header(u'登录方式', 'lib.form_header'),
    #     'ways',
    #     rules.Header(u'网站登录执行', 'lib.form_header'),
    #     'type', 'jscode', 'pycode',
    #     rules.Header(u'二维码登录', 'lib.form_header'),
    #     'qrcode', 'qrcode_jscode',
    #     rules.Header(u'登录事件', 'lib.form_header'),
    #     'events'
    #     # rules.Header(u'二次登录验证', 'lib.form_header'),
    #     # 'ssiv',
    #     # 'ssiv_get_type', 'ssiv_get_jscode', 'ssiv_get_pycode',
    #     # 'ssiv_verify_type', 'ssiv_verify_jscode', 'ssiv_verify_pycode'
    # ]

    # form_args = {
    #     'ways': {
    #         'render_kw': {
    #             'columns': 1
    #         }
    #     },
    #     'events': {
    #         'render_kw': {
    #             'columns': 1
    #         }
    #     }
    # }

    form_widget_args = {
        'jscode': {
            'data-role': 'editor',
            'data-lang': 'javascript',
            'data-min-lines': 20,
            'data-max-lines': 50
        },
        'pycode': {
            'data-role': 'editor',
            'data-lang': 'python',
            'data-min-lines': 20,
            'data-max-lines': 50
        },
    }

    def enable_action(self, obj):
        xconf.set_action(obj.project.alias, obj.alias, obj.to_conf())
        obj.status = STATUS_ENABLE
        obj.published = datetime.now()
        obj.save()
        # self.logger.info(u'启用动作 %s', obj.alias, extra={'project': obj.project.alias, 'action': obj.alias})
        return obj

    def disable_action(self, obj):
        # if obj.status == STOP:
        #     return

        xconf.del_action(obj.project.alias, obj.alias)
        obj.status = STATUS_DISABLE
        obj.save()
        # self.logger.info(u'停用动作 %s', obj.alias, extra={'project': obj.project.alias, 'action': obj.alias})
        return obj

    @action('enable', u'启用')
    def a_enable_conf(self, ids):
        actions = []
        for id in ids:
            obj = self.get_one(id)
            if self.enable_action(obj):
                actions.append(obj.name)

        if actions:
            flash(u'成功启用以下动作设置.<br />%s' % ', '.join(actions), 'success')

    @action('stop', u'停用')
    def c_disable_conf(self, ids):
        actions = []
        for id in ids:
            obj = self.get_one(id)
            if self.disable_action(obj):
                actions.append(obj.name)

        flash(u'成功停用以下动作设置.<br />%s' % ', '.join(actions), 'success')

    @expose('/check/', methods=['POST'])
    def check(self):
        pass
