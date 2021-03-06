# coding=utf8

import time
import json
from datetime import datetime
from flask import current_app, flash, jsonify, request
from jinja2 import Markup
from flask_admin import expose
from flask_admin.actions import action
# from flask_admin.form import rules
from yunduo.conf import xconf
# from yunduo.utils import parse_rate
from xadmin.view.base import BaseView
# from xadmin.base.rules import Row, Column
from xadmin.utils.format import date_format, map_format
from xadmin.helpers import set_current_project
from xadmin.constant import STATUS_ENABLE, STATUS_DISABLE
# from xadmin.rabbitq import get_queues

# from connections import redis_conf, redis_df
# from xspider.app import app as celery_app
# from xspider.tasks import crawl


class BlockView(BaseView):
    inject_current_project = True
    can_view_details = False
    # details_modal = True
    # details_modal_template = 'admin/model/modals/project_details.html'

    column_list = ['name', 'project', 'owner', 'created']
    column_filters = ['name']

    column_labels = {
        'name': u'名称',
        'alias': u'别名',
        'type': u'类型',
        'status': u'状态',
        'owner': u'创建者',

        'created': u'新增时间',
        'updated': u'更新时间',
        'published': u'发布时间'

    }

    column_searchable_list = ('name', )
    column_formatters = {
        # 'name': _project_pages_index,
        # 'status': map_format({START: u'启用', PAUSE: u'暂停', STOP: u'停用'}),
        'created': date_format,
        'updated': date_format,
        'published': date_format,
    }

    form_subdocuments = {
        'rules': {
            'form_subdocuments': {
                None: {
                    'form_choices': {
                        'field': [('dlcount', '下载数'), ('rule', u'规则抽取'), ('code', u'Py代码抽取')],
                        'window': [(60, '1分钟'), (300, '5分钟'), (900, '15分钟'), (1800, '30分钟'), (3600, '60分钟')],

                    }
                }
            }
        }
    }

    # form_rules = ['name', 'alias']

    form_widget_args = {

    }

    def enable_blocked(self, obj):
        old_blocked = xconf.get_blocked(obj.project.alias)

        xconf.set_blocked(obj.project.alias, obj.alias, obj.to_conf())
        obj.status = STATUS_ENABLE
        obj.published = datetime.now()
        obj.save()
        self.logger.info(u'启用屏蔽检测策略 %s', obj.alias, extra={'project': obj.project.alias, 'blocked': obj.alias})
        return obj

    def disable_blocked(self, obj):
        xconf.del_blocked(obj.project.alias, obj.alias)
        obj.status = STATUS_DISABLE
        obj.save()
        self.logger.info(u'停用屏蔽检测策略 %s', obj.alias, extra={'project': obj.project.alias, 'blocked': obj.alias})
        return obj
