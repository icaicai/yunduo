# coding=utf8

import time
import json
from datetime import datetime
from flask import current_app, flash, jsonify, request
from jinja2 import Markup
from flask_admin import expose
from flask_admin.actions import action
# from flask_admin.form import rules
# from yunduo.utils import parse_rate
from xadmin.view.base import BaseView
# from xadmin.base.rules import Row, Column
from xadmin.utils.format import date_format, map_format
from xadmin.helpers import set_current_project
# from xadmin.constant import STOP, PAUSE, START
# from xadmin.rabbitq import get_queues

# from connections import redis_conf, redis_df
# from xspider.app import app as celery_app
# from xspider.tasks import crawl


def _project_pages_index(view, context, model, name):
        return Markup(
            u"<a href='%s'>%s</a>" % (
                view.get_url('.jump', id=model.id),
                model.name
            )
        ) if model.name else u""


# Customized admin views
class ProjectView(BaseView):
    inject_current_project = True
    can_view_details = False
    # details_modal = True
    # details_modal_template = 'admin/model/modals/project_details.html'

    column_list = ['name', 'alias', 'owner', 'created']
    column_filters = ['name', 'alias']

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

    column_searchable_list = ('name', 'alias')
    column_formatters = {
        'name': _project_pages_index,
        # 'status': map_format({START: u'启用', PAUSE: u'暂停', STOP: u'停用'}),
        'created': date_format,
        'updated': date_format,
        'published': date_format,
    }

    form_ajax_refs = {
        '__self__': {
            'fields': ('name', 'alias')
        }
    }

    form_rules = ['name', 'alias']

    form_widget_args = {

    }

    @expose('/jump')
    def jump(self):
        project_id = request.values.get('id')
        project = self.get_one(project_id)
        set_current_project(project)
        # return jsonify(True)
        url = self.get_url('page.index_view')
        return self.redirect(url)

    @expose('/choose')
    def choose(self):
        project_id = request.values.get('id')
        project = self.get_one(project_id)
        set_current_project(project)
        return jsonify(True)
        # obj = self.get_one(id)
        # q = get_queues(obj.alias, obj.type == 1)
        # return jsonify(q)

