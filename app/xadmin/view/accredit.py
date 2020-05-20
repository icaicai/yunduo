# coding=utf8

import json
from datetime import datetime
from flask import current_app, flash
from flask_admin import expose
from flask_admin.actions import action
from flask_admin.helpers import get_form_data
from flask_admin.form import rules
from xadmin.view.base import BaseView
from xadmin.utils.format import date_format, map_format
from xadmin.constant import STATUS_ENABLE, STATUS_DISABLE
from xadmin.base.rules import Row, Column
# from connections import redis_conf


# Customized admin views
class AccreditView(BaseView):

    # edit_template = 'admin/model/login_edit.html'
    # create_template = 'admin/model/login_create.html'

    column_list = ['name', 'project', 'category', 'status', 'updated', 'published']
    # column_filters = ['name', 'alias']

    column_labels = {
        'name': u'名称',
        'alias': u'代码',
        'category': u'类别',
        'project': u'关联项目',
        'tags': u'标签',
        'status': u'状态',
        'type': u'代码类型',

        # 'jscode': u'Js代码',
        # 'pycode': u'Py代码',
        #
        # 'qrcode': u'二维码登录',
        # 'qrcode_jscode': u'Js代码',

        'ways': u'登录方式',
        # 'events': u'登录过程',

        'created': u'新增时间',
        'updated': u'更新时间',
        'published': u'发布时间'

    }

    column_searchable_list = ('name',)
    column_formatters = {
        # 'name': _project_pages_index,
        'status': map_format({STATUS_ENABLE: u'启用', STATUS_DISABLE: u'停用'}),
        # 'type': map_format({0: u'通用', 1: u'存储', 2: u'告警'}),
        'created': date_format,
        'updated': date_format,
        'published': date_format,
    }
    # # form_ajax_refs = {
    # #     'entry_page': {
    # #         'model': 'Page',
    # #         'fields': ('name',)
    # #     }
    # # }

    # form_rules = [
    #     Row(Column('name'), Column('alias')),
    #     Row(Column('category'), Column('project')),
    #     rules.Header(u'登录方式', 'lib.form_header'),
    #     'ways',
    # ]

    form_args = {
        'ways': {
            'render_kw': {
                'columns': 1
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
        'ways': {
            'form_subdocuments': {
                None: {
                    'column_labels': {
                        'title': u'名称',
                        'default': u'默认',
                        'fields': u'登录字段',
                        'action': '登录动作'
                    },
                    'form_rules': ('title', 'action', 'fields'),
                    'form_ajax_refs': {
                        'action': {
                            'fields': ('name', 'alias'),
                            'filters': {
                                'status': STATUS_ENABLE
                            }
                        }
                    },
                    'form_args': {
                        'fields': {
                            'render_kw': {
                                'columns': 1
                            }
                        }
                    },
                    'form_widget_args': {
                        'title': {
                            'append': {'name': 'default'}
                        }
                    },
                    'form_subdocuments': {
                        'fields': {
                            'form_subdocuments': {
                                None: {
                                    'column_labels': {
                                        'name': u'字段名称',
                                        'default': u'默认值',
                                        'label': u'字段标题',
                                        'type': u'字段类型',
                                        'props': u'附加属性',
                                    },
                                    'form_rules': (Row(Column('name'), Column('label')),
                                                   Row(Column('type'), Column('default')),
                                                   'props'),
                                    'form_ajax_refs': {
                                        'action': {
                                            'fields': ('name', 'alias'),
                                            'filters': {
                                                'status': STATUS_ENABLE
                                            }
                                        }
                                    },
                                    'form_widget_args': {
                                        'props': {
                                            'data-role': 'editor',
                                            'data-lang': 'javascript',
                                            'data-max-lines': 10
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


    @action('enable', u'启用')
    def a_enable_conf(self, ids):
        scripts = []
        errs = []
        for id in ids:
            obj = self.get_one(id)
            if not obj.project.entry_page:
                errs.append(u'请先登录 <b>%s</b> 设置关联的项目的入口页' % obj.name)
            elif self.enable_login(obj):
                scripts.append(obj.name)

        if errs:
            flash(u'%s' % u'<br />\n'.join(errs), 'error')
        if scripts:
            flash(u'成功启用以下登录设置.<br />%s' % ', '.join(scripts), 'success')

    @action('stop', u'停用')
    def c_disable_conf(self, ids):
        scripts = []
        for id in ids:
            obj = self.get_one(id)
            if self.disable_login(obj):
                scripts.append(obj.name)

        flash(u'成功停用以下登录设置.<br />%s' % ', '.join(scripts), 'success')

