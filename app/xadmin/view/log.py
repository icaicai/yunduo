# coding=utf8

import html
import pymongo
from jinja2 import Markup
from flask import request, redirect, flash
from flask_admin import expose
from flask_admin.babel import gettext
from flask_admin.helpers import get_redirect_target
from flask_admin.model import template
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_admin.contrib.pymongo import filters
# from connections import mongo_log
from yunduo.resource import get_connection
from xadmin.utils.format import date_format, map_format
from xadmin.view.base import MongoView


def message_format(view, context, model, name):
    if 'exception' in model:
        exc = model['exception']
        s = '''<div data-toggle="popover" data-trigger="hover" title="%s" data-content="%s">
<i class="icon fa fa-warning text-red"></i>%s</a>''' \
            % (html.escape(exc['message'], True), html.escape('<pre>%s</pre>' % exc['trace'], True), model[name])
        return Markup(s)
    else:
        return model[name]


class EndpointLinkRowAction(template.BaseListRowAction):
    def __init__(self, icon_class, endpoint, title=None, id_arg='id', id_field='id', url_args=None):
        super(EndpointLinkRowAction, self).__init__(title=title)

        self.icon_class = icon_class
        self.endpoint = endpoint
        self.id_arg = id_arg
        self.id_field = id_field
        self.url_args = url_args

    def render(self, context, row_id, row):
        m = self._resolve_symbol(context, 'row_actions.link')
        get_url = self._resolve_symbol(context, 'get_url')
        meta = row.get('meta')
        if not meta or self.id_field not in row:
            return ''

        kwargs = dict(self.url_args) if self.url_args else {}
        kwargs[self.id_arg] = row[self.id_field]

        view = context['admin_view']
        url = get_url(self.endpoint, **kwargs)

        return m(self, url)


page_db = get_connection('page')
log_db = get_connection('log')
task_db = get_connection('task')
log_task_coll = task_db['task_infos']
log_page_coll = page_db['page_infos']
log_log_coll = log_db['task_logs']


class LogView(MongoView):

    collection = log_log_coll

    column_list = ('meta.project', 'meta.job', 'meta.page', 'level', 'meta.worker',     # 'meta.task_id',
                   'message', 'created')

    column_filters = (filters.FilterEqual('project', u'关联项目'),
                      filters.FilterEqual('page', u'关联页面'),
                      filters.FilterEqual('task_id', u'关联任务'),
                      filters.FilterEqual('level', u'日志级别'))

    column_labels = {

        'meta.project': u'关联项目',
        'meta.job': u'关联任务',
        'meta.page': u'关联页面',
        'meta.action': u'关联动作',
        'meta.task_id': u'相关任务',
        'level': u'日志级别',
        # 'worker': u'日志级别',
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

    column_display_actions = True

    column_extra_row_actions = [EndpointLinkRowAction('fa fa-tasks', 'log.get_task_info', id_field='task_id'),
                                EndpointLinkRowAction('fa fa-file-code-o', 'log.get_page_info', id_field='task_id')]


    # def initialize(self):
    #     if self.coll_name == 'crawl':
    #         self.column_list = ('_project', '_page', '_task_id', 'level', '_worker', 'message', '_created')
    #     else:
    #         self.column_list = ('_code', '_action', '_task_id', 'level', '_worker', 'message', '_created')

    def _get_default_order(self):
        return ('created', 1)

    # def get_list(self, page, sort_column, sort_desc, search, filters,
    #              execute=True, page_size=None):
    #     task_infos = self.db.task_infos
    #     task_logs = self.db.task_logs

    # def get_list(self, page, sort_column, sort_desc, search, filters,
    #              execute=True, page_size=None):
    #     """
    #         Get list of objects from MongoEngine
    #
    #         :param page:
    #             Page number
    #         :param sort_column:
    #             Sort column
    #         :param sort_desc:
    #             Sort descending
    #         :param search:
    #             Search criteria
    #         :param filters:
    #             List of applied fiters
    #         :param execute:
    #             Run query immediately or not
    #         :param page_size:
    #             Number of results. Defaults to ModelView's page_size. Can be
    #             overriden to change the page_size limit. Removing the page_size
    #             limit requires setting page_size to 0 or False.
    #     """
    #     # db.hotel.aggregate([
    #     #   { $sort: { url: -1 } },
    #     #   { $group: {_id: "$url"} },
    #     #   { $skip: 40 },
    #     #   { $limit: 30 }
    #     # ])
    #     # db.collection.distinct(field, query, options)                   <================
    #
    #     query = {}
    #
    #     # Filters
    #     if self._filters:
    #         data = []
    #
    #         for flt, flt_name, value in filters:
    #             f = self._filters[flt]
    #             data = f.apply(data, value)
    #
    #         if data:
    #             if len(data) == 1:
    #                 query = data[0]
    #             else:
    #                 query['$and'] = data
    #
    #     # Search
    #     if self._search_supported and search:
    #         query = self._search(query, search)
    #
    #     # Get count
    #     count = self.coll.find(query).count() if not self.simple_list_pager else None
    #
    #     # Sorting
    #     sort_by = None
    #
    #     if sort_column:
    #         sort_by = [(sort_column, pymongo.DESCENDING if sort_desc else pymongo.ASCENDING)]
    #     else:
    #         order = self._get_default_order()
    #
    #         if order:
    #             sort_by = [(order[0], pymongo.DESCENDING if order[1] else pymongo.ASCENDING)]
    #
    #     # Pagination
    #     if page_size is None:
    #         page_size = self.page_size
    #
    #     skip = 0
    #
    #     if page and page_size:
    #         skip = page * page_size
    #     projection = {"_id": 1, "meta": 1}
    #     results = task_infos.find(query, projection=projection, sort=sort_by, skip=skip, limit=page_size)
    #
    #     if execute:
    #         rows = []
    #         for row in results:
    #             rows.append(row)
    #             row["logs"] = list(task_logs.find({"meta.task_id": row["_id"]}))
    #         # results = list(results)
    #
    #     return count, results

    @expose('/task-info/')
    def get_task_info(self):
        task_id = get_mdict_item_or_list(request.args, 'id')
        print('task_id ==> ', task_id)
        task = log_task_coll.find_one({'task_id': self._get_valid_id(task_id)})
        tmpl = 'admin/model/log_task_info.html'
        return self.render(tmpl,
                           # get_value=self.get_list_value,
                           get_value=lambda m, c: m[c],
                           get_type=type,
                           model=task)

    @expose('/page-info/')
    def get_page_info(self):
        return_url = get_redirect_target() or self.get_url('.index_view')
        task_id = get_mdict_item_or_list(request.args, 'id')
        page = log_page_coll.find({'task_id': task_id})

        if page.count() < 1:
            flash('没找到相关任务的页面Response信息', 'error')
            return redirect(return_url)

        tmpl = 'admin/model/log_page_info.html'
        return self.render(tmpl,
                           # get_value=self.get_list_value,
                           get_value=lambda m, c: m[c],
                           get_type=type,
                           model=page)



'''
Project 有3个log
1. task log / crawl、action
2. task info
3. page info

关联查询任务信息和日志
不对日志进行过滤时：
db.crawl_task_infos.aggregate([
	{$project: {kwargs: 0}},
	{ "$sort": { "received": -1 } },
	{$limit: 10},
	{ "$sort": { "received": -1 } },
    { "$limit": 10 },
	{ "$lookup": {       
       from: "crawl_task_logs",
       localField:"_id",
       foreignField: "_task_id",
       as: "logs"
	},
])       

对日志进行过滤时

'''
