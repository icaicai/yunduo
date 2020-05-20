# coding=utf8

import json
from datetime import datetime
from flask import current_app, flash
from flask_admin import expose
from flask_admin.actions import action
from flask_admin.helpers import get_form_data
from flask_admin.form import rules, Select2Field
from yunduo.conf import xconf
from xadmin.view.base import BaseView
from xadmin.utils.format import date_format, map_format, edit_link_format
from xadmin.constant import STATUS_ENABLE, STATUS_DISABLE
from xadmin.base.rules import Row, Column
# from connections import redis_conf


# Customized admin views
class FormView(BaseView):
    inject_current_project = True
    # edit_template = 'admin/model/login_edit.html'
    # create_template = 'admin/model/login_create.html'

    column_list = ['name', 'project', 'tags', 'sequence', 'status', 'updated', 'published']
    # column_filters = ['name', 'alias']

    column_labels = {
        'name': u'名称',
        'alias': u'别名',
        'tags': u'类别',
        'project': u'关联项目',
        'sequence': u'排序',
        'status': u'状态',
        'type': u'代码类型',
        'action': '表单动作',
        'job': '关联任务',

        # 'jscode': u'Js代码',
        # 'pycode': u'Py代码',
        #
        # 'qrcode': u'二维码登录',
        # 'qrcode_jscode': u'Js代码',

        'fields': u'字段',
        # 'ways': u'登录方式',
        # 'events': u'登录过程',

        'created': u'新增时间',
        'updated': u'更新时间',
        'published': u'发布时间'

    }

    column_searchable_list = ('name',)
    column_formatters = {
        'name': edit_link_format,
        'status': map_format({STATUS_ENABLE: u'启用', STATUS_DISABLE: u'停用'}),
        # 'type': map_format({0: u'通用', 1: u'存储', 2: u'告警'}),
        'created': date_format,
        'updated': date_format,
        'published': date_format,
    }

    form_rules = [
        'project',
        Row(Column('name'), Column('sequence')),
        Row(Column('alias'), Column('tags')),
        # 'name',
        # 'alias',
        # 'sequence',
        Row(Column('action'), Column('job')),
        'fields'
        # Row(Column('name'), Column('alias')),
        # Row(Column('category'), Column('project')),
        # rules.Header(u'登录方式', 'lib.form_header'),
        # 'ways',
    ]

    form_ajax_refs = {
        'action': {
            'fields': ('name', 'alias'),
            # 'filters': {
            #     'status': STATUS_ENABLE
            # }
        },
        'job': {
            'fields': ('name', 'alias'),
            'filters': {
                'type': 2
            }
        }
    }

    form_args = {
        'project': {
            'readonly': 'readonly'
        },
        'tags': {
            'render_kw': {
                # 'data-role': 'select2',
                # 'data-custom-input': '1'
            }
        }
    }

    form_widget_args = {
        'jscode': {
            'data-role': 'editor',
            'data-lang': 'javascript',
            'data-min-lines': 3,
            'data-max-lines': 30
        },
        'pycode': {
            'data-role': 'editor',
            'data-lang': 'python',
            'data-min-lines': 3,
            'data-max-lines': 30
        },
        'qrcode_jscode': {
            'data-role': 'editor',
            'data-lang': 'javascript',
            'data-min-lines': 3,
            'data-max-lines': 30
        },
    }

    form_subdocuments = {
        'fields': {
            'form_subdocuments': {
                None: {
                    'column_labels': {
                        'name': '字段名称',
                        'default': '默认值',
                        'label': '字段标题',
                        'type': '字段类型',
                        'action': '事件动作',
                        'trigger': '自动触发事件动作',
                        'props': '附加属性',
                    },
                    'form_rules': (Row(Column('name', 'label', 'type', 'default'),
                                       Column('action', 'trigger', 'props')), ),
                    'form_ajax_refs': {
                        'action': {
                            'fields': ('name', 'alias'),
                            # 'filters': {
                            #     'status': STATUS_ENABLE
                            # }
                        }
                    },
                    'form_widget_args': {
                        'props': {
                            'data-role': 'editor',
                            'data-lang': 'javascript',
                            'data-min-lines': 3,
                            'data-max-lines': 10
                        }
                    }
                }
            }
        }
    }

    def enable_login(self, obj):
        xconf.set_form(obj.project.alias, obj.alias, obj.to_conf())
        obj.status = STATUS_ENABLE
        obj.published = datetime.now()
        obj.save()
        self.logger.info(u'启用登录方法 %s', obj.alias, extra={'project': obj.project.alias, 'login': obj.alias})
        return obj

    def disable_login(self, obj):
        # if obj.status == STOP:
        #     return

        xconf.del_form(obj.project.alias, obj.alias)
        obj.status = STATUS_DISABLE
        obj.save()
        self.logger.info(u'停用登录方法 %s', obj.alias, extra={'project': obj.project.alias, 'login': obj.alias})
        return obj

    @action('enable', u'启用')
    def a_enable_conf(self, ids):
        ways = []
        for id in ids:
            obj = self.get_one(id)
            if self.enable_login(obj):
                ways.append(obj.name)

        if ways:
            flash(u'成功启用以下登录方法.<br />%s' % ', '.join(ways), 'success')

    @action('stop', u'停用')
    def c_disable_conf(self, ids):
        ways = []
        for id in ids:
            obj = self.get_one(id)
            if self.disable_login(obj):
                ways.append(obj.name)

        flash(u'成功停用以下登录方法.<br />%s' % ', '.join(ways), 'success')

