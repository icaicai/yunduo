# coding=utf8

import cgi
from jinja2 import Markup
from wtforms import form
from flask import (request, redirect, flash)

from flask_admin import expose
from flask_admin.model import template
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_admin.helpers import get_redirect_target
from flask_admin.babel import gettext
from flask_admin.contrib.pymongo import ModelView, filters
# from connections import mongo_log
from yunduo.resource import get_connection
from xadmin.utils.format import date_format, map_format
from xadmin.view.base import MongoView


mongo_logs = get_connection('log')
PageDB = get_connection('page')


def message_format(view, context, model, name):
    if 'exception' in model:
        exc = model['exception']
        s = '<div data-toggle="popover" data-trigger="hover" title="%s" data-content="%s">%s</a>' \
            % (cgi.escape(exc['message'], True), cgi.escape('<pre>%s</pre>' % exc['stackTrace'], True), model[name])
        return Markup(s)
    else:
        return model[name]


class TaskView(MongoView):

    collections_map = {
        'crawl': mongo_logs.crawl_task_infos,
        'authorized': mongo_logs.authorized_task_infos
    }

    can_view_details = True
    details_template = 'admin/model/task_details.html'

    column_details_list = ("_id", "_project", "_page", "_url", "_custom_id", "kwargs", "name", "received", "succeeded",
                           "root_id", "parent_id", "runtime", "retries", "eta", "expires", "result")
    column_list = ('_id', '_name', '_project', '_page', 'parent_id', 'root_id')


    # column_filters = (filters.FilterEqual('project', u'项目'),
    #                   filters.FilterEqual('page', u'页面'),
    #                   filters.FilterEqual('level', 'Name'))

    column_labels = {

        'project': u'关联项目',
        'page': u'关联页面',
        'task_id': u'关联任务',
        'level': u'日志级别',
        'message': u'信息',

        'created': u'记录时间',
    }

    column_formatters = {
        'message': message_format,
        # 'status': map_format({START: u'启用', PAUSE: u'暂停', STOP: u'停用'}),
        # 'category': map_format({'ds': u'电商', 'sb': u'社保', 'dx': u'电信运营商'}),
        # 'type': map_format({0: u'通用', 1: u'存储', 2: u'告警'}),
        'created': date_format,
    }

    column_extra_row_actions = [template.EndpointLinkRowAction('fa fa-file-code-o', '.get_page')]


    def initialize(self):
        if self.coll_name == 'crawl':
            self.column_list = ('_id', 'name', '_project', '_page', 'parent_id', 'root_id')
        else:
            self.column_list = ('_id', 'name', '_code', '_action', 'parent_id', 'root_id')


    @expose('/page/')
    def get_page(self):
        return_url = get_redirect_target() or self.get_url('.index_view')

        task_id = get_mdict_item_or_list(request.args, 'id')
        task = self.get_one(task_id)

        if task is None:
            flash(gettext('Record does not exist.'), 'error')
            return redirect(return_url)

        if self.coll_name == 'crawl':
            colname = 'crawl_%s' % task['_project']
        else:
            colname = 'auth_%s' % task['_code']
        # print PageDB[colname]
        coll = PageDB[colname]
        page = coll.find({'_task_id': self._get_valid_id(task_id)})
        page = list(page)
        if not page:
            flash(gettext('Record does not exist.'), 'error')
            return redirect(return_url)

        tmpl = 'admin/model/task_page_info.html'
        return self.render(tmpl,
                           # get_value=self.get_list_value,
                           get_value=lambda m, c: m[c],
                           get_type=type,
                           model=page)
