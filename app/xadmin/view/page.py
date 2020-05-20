# coding=utf8

import json
from datetime import datetime
from flask import current_app, flash, request, jsonify
from jinja2 import Markup
from wtforms.validators import DataRequired, URL, ValidationError
from werkzeug.datastructures import ImmutableMultiDict
from flask_admin import expose
from flask_admin.actions import action
from flask_admin.helpers import get_form_data, get_redirect_target, flash_errors
from flask_admin.form import FormOpts, rules
from flask_admin.model.template import TemplateLinkRowAction
from flask_admin.contrib.mongoengine.form import get_form
from flask_admin.babel import gettext
from yunduo.conf import xconf

from xadmin.base.rules import Row, Column
from xadmin.view.base import BaseView
from xadmin.base.validators import ConditionRequired
from xadmin.utils.format import date_format, map_format, edit_link_format
from xadmin.constant import STATUS_DISABLE, STATUS_ENABLE
# from connections import redis_conf
from xadmin.helpers import current_project


# class EntryRowAction(TemplateLinkRowAction):
#     def __init__(self):
#         super(EntryRowAction, self).__init__(
#             'row_actions.entry_row',
#             u'设为入口页')


def _project_pages_index(view, context, model, name):
        return Markup(
            u"<a href='%s'>%s</a>" % (
                view.get_url('page.index_view', flt0_0=model.project.id),
                model.project.name
            )
        ) if model.project.name else u""


# def _pages_edit(view, context, model, name):
#     view_args = view._get_list_extra_args()
#     return_url = view._get_list_url(view_args)
#     return Markup(
#         u"<a href='%s'>%s</a>" % (
#             view.get_url('.edit_view', id=model.id, url=return_url),
#             model.name
#         )
#     )


class PageView(BaseView):
    inject_current_project = True
    edit_template = 'admin/model/page_edit.html'
    create_template = 'admin/model/page_create.html'

    column_list = ['name', 'alias', 'project', 'status', 'updated', 'published']
    column_filters = ['project']
    column_searchable_list = ['name', 'alias']
    column_formatters = {
        'name': edit_link_format,
        # 'project': _project_pages_index,
        'status': map_format({STATUS_ENABLE: u'启用', STATUS_DISABLE: u'停用'}),
        'created': date_format,
        'updated': date_format,
        'published': date_format,
    }

    # column_extra_row_actions = [EntryRowAction()]

    column_labels = {
        'name': u'页面名称',
        'alias': u'别名',
        'status': u'状态',
        'project': u'所属项目',
        'method': u'抓取方式',
        'encoding': u'页面编码',
        'headers': u'自定义HTTP头',
        # 'is_entry': u'入口页',
        # 'data': u'提交数据',

        'test_html': u'测试用HTML',
        'test_url': u'测试用URL',
        'test_conf': u'测试用设置',

        'before_request': u'请求处理',
        'after_response': u'响应处理',

        'js_enable': u'启用JS',
        'js_code': u'JS判断代码',
        'js_timeout': u'JS超时时间',

        'link_type': u'抽取类型',
        'link_rules': u'抽取规则',
        'link_pycode': u'抽取Py代码',

        'item_type': u'解析类型',
        'item_fields': u'解析字段',
        'item_pycode': u'解析Py代码',
        'item_save_script': u'保存脚本',
        'save_script': u'保存脚本',

        'created': u'新增时间',
        'updated': u'更新时间',
        'published': u'发布时间'

    }

    form_choices = {
        'link_type': [('', u'不抽取'), ('rule', u'规则抽取'), ('code', u'Py代码抽取')]
    }
    form_overrides = {
        # 'project': HiddenModelSelectField
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
        'test_url': {
            'validators': [DataRequired(), URL()],
            'render_kw': {
                'placeholder': u'如 https://www.python.org/downloads/'
            }
        },
        'link_rules': {
            'validators': [ConditionRequired(lambda frm, fld: frm['link_type'].data == 'conf', u'请设置链接抽取规则')],
        },
        'link_pycode': {
            'validators': [ConditionRequired(lambda frm, fld: frm['link_type'].data == 'code', u'请编写链接抽取代码')],
        },
        'item_fields': {
            'validators': [ConditionRequired(lambda frm, fld: frm['item_type'].data == 'conf', u'请设置字段解析规则')],
        },
        'item_pycode': {
            'validators': [ConditionRequired(lambda frm, fld: frm['item_type'].data == 'code', u'请编写内容解析代码')],
        },
        # 'item_save_script': {
        #     'validators': [ConditionRequired(lambda frm, fld: frm['item_type'].data and frm['project'].data.type == 0,
        #                                      u'请选择内容保存脚本')],
        # }
    }

    form_widget_args = {
        'headers': {
            'data-role': 'editor',
            'data-lang': 'json',
            'data-min-lines': 10,
            'data-max-lines': 10
        },
        'js_code': {
            'data-role': 'editor',
            'data-lang': 'javascript',
            'data-max-lines': 10
        },
        'test_html': {
            'data-role': 'editor',
            'data-lang': 'html',
            'data-max-lines': 20
        },
        'test_conf': {
            'data-role': 'editor',
            'data-lang': 'json',
            'data-max-lines': 10
        },
        'before_request': {
            'data-role': 'editor',
            'data-lang': 'python',
            'data-min-lines': 5,
            'data-max-lines': 30
        },
        'after_response': {
            'data-role': 'editor',
            'data-lang': 'python',
            'data-min-lines': 5,
            'data-max-lines': 30
        },
        'link_pycode': {
            'data-role': 'editor',
            'data-lang': 'python',
            'data-min-lines': 10,
            'data-max-lines': 30
        },
        'item_pycode': {
            'data-role': 'editor',
            'data-lang': 'python',
            'data-min-lines': 10,
            'data-max-lines': 30
        }
    }

    form_rules = [
        'project',
        Row(Column('name', 'alias',
                   Row(Column('method'), Column('encoding')),
                   Row(Column('js_enable'), Column('js_timeout'))),
            Column('headers')),
        'js_code',
        rules.Header(u'测试设置', 'lib.form_header'),
        'test_url',
        'test_conf',
        'test_html',
        rules.Header(u'下载处理', 'lib.form_header'),
        'before_request',
        'after_response',
        rules.Header(u'链接抽取设置', 'lib.form_header'),
        'link_type',
        'link_rules',
        'link_pycode',
        rules.Header(u'内容解析设置', 'lib.form_header'),
        'item_type',
        # 'item_save_script',
        'item_fields',
        'item_pycode',
        'save_script'
    ]

    # create_modal = True
    # edit_modal = True
    # modal_window_class = 'large-dialog'
    # column_filters = [
    #     FilterEqual(column=Post.value, name=u'类型', options=(('2', u'特殊'), ('0', u'普通'))),
    # ]
    # column_editable_list = ['name']

    form_subdocuments = {
        # 'project': {
        #     'form_rules': ('type', ),
        # },
        'link_rules': {
            'form_subdocuments': {
                None: {
                    # Add <hr> at the end of the form
                    'form_rules': ('page', 'selector', 'df_enable', 'allows', 'denies'),
                    'form_ajax_refs': {
                        'page': {
                            # 'model': 'Page',
                            'fields': ['name', 'alias']
                        }
                    },
                    'column_labels': {
                        'page': u'关联页面',
                        'selector': u'选择器',
                        'df_enable': u'URL去重',
                        'allows': u'URL允许',
                        'denies': u'URL禁止',
                        'process_value': u'URL处理'
                    },
                    # 'form_override': {
                    #     'page': {

                    #     }
                    # },
                    'form_widget_args': {
                        'page': {
                            'data-filters': 'project',
                            'append': {
                                'class': 'input-group-btn',
                                # 'content': '<button class="btn btn-info add-page"><i class="fa fa-plus"></i></button>'
                                'content': ('<a class="btn btn-primary new-page-simple"'
                                            'title="创建新页面" ><i class="fa fa-plus-circle"></i></a>')
                            }
                        },
                        'selector': {
                            'prepend': {'name': 'sel_type'}
                        },
                        'allows': {
                            'row_class': 'extend-attr'
                        },
                        'denies': {
                            'row_class': 'extend-attr'
                        }
                    }
                }
            }
        },
        'item_fields': {
            'form_subdocuments': {
                None: {
                    'form_rules': ('name', 'selector', 'default'),
                    'column_labels': {
                        'name': u'字段名',
                        'required': u'必需',
                        'selector': u'选择器',
                        'default': u'默认值',
                        'process_value': u'值处理'
                    },
                    'form_widget_args': {
                        'selector': {
                            'prepend': {'name': 'sel_type'}
                        },
                        'name': {
                            'append': {'name': 'required'}
                        }
                    }
                }
            }
        }
    }

    def _refresh_forms_cache(self):
        # from wtforms.fields import HiddenField
        # from wtforms.validators import InputRequired

        super(PageView, self)._refresh_forms_cache()
        self._form_simple_create_class = get_form(
            self.model, self.model_form_converter(self), base_class=self.form_base_class,
            only=('project', 'name', 'alias'), exclude=self.form_excluded_columns,
            field_args=self.form_args, extra_fields=self.form_extra_fields)

        # class EntryForm(self.form_base_class):
        #     id = HiddenField(validators=[InputRequired()])
        #     url = HiddenField()
        #
        # self._entry_form_class = EntryForm

    def _refresh_form_rules_cache(self):
        super(PageView, self)._refresh_form_rules_cache()
        self._form_simple_create_rules = rules.RuleSet(self, ['project', 'name', 'alias'])

    # def entry_form(self):
    #     if request.form:
    #         return self._entry_form_class(request.form)
    #     elif request.args:
    #         # allow request.args for backward compatibility
    #         return self._entry_form_class(request.args)
    #     else:
    #         return self._entry_form_class()
    #
    # def _index_render_kw(self):
    #     return {'entry_form': self.entry_form()}

    # def on_model_delete(self, model):
    #     # print('page on_model_delete', model.is_entry)
    #     if model.is_entry:
    #         raise ValidationError(u'入口页面，不能删除')

    def create_simple_form(self, obj=None):
        return self.create_form(obj, self._form_simple_create_class)
        # data = get_form_data()
        # if not data:
        #     params = self.get_extra_filters()
        #     data = ImmutableMultiDict(params)

        # return self._form_simple_create_class(data, obj=obj)

    def enable_page(self, obj):
        xconf.set_page(obj.project.alias, obj.alias, obj.to_conf())
        obj.status = STATUS_ENABLE
        obj.published = datetime.now()
        obj.save()
        self.logger.info(u'启用页面 %s', obj.alias, extra={'project': obj.project.alias, 'page': obj.alias})
        return obj

    def disable_page(self, obj):
        # if obj.status == STOP:
        #     return

        xconf.del_page(obj.project.alias, obj.alias)
        obj.status = STATUS_DISABLE
        obj.save()
        self.logger.info(u'停用页面 %s', obj.alias, extra={'project': obj.project.alias, 'page': obj.alias})
        return obj

    @expose('/simple/', methods=['GET', 'POST'])
    def simple_new(self):
        form = self.create_simple_form()

        if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:
            self._validate_form_instance(ruleset=self._form_create_rules, form=form)

        if self.validate_form(form):
            # in versions 1.1.0 and before, this returns a boolean
            # in later versions, this is the model itself
            model = self.create_model(form)
            if model:
                return jsonify({
                    "status": "success",
                    "message": gettext('Record was successfully created.')
                })
                # scripts = []
                # # flash(gettext('Record was successfully created.'), 'success')
                # tmpl = u"iziToast.success({message: '%s', position: 'center'});"
                # scripts.append(tmpl % (gettext('Record was successfully created.')))
                # scripts.append('$("#modal_window_add_page").modal("hide");')
                # return u'<script language="javascript">%s</script>' % ('\n'.join(scripts), )

        form_opts = FormOpts(widget_args=self.form_widget_args,
                             form_rules=self._form_simple_create_rules)
        template = 'admin/model/modals/model_simple_create.html'
        return self.render(template,
                           form=form,
                           form_opts=form_opts,
                           return_url='')

    @action('enable', u'启用')
    def a_enable_conf(self, ids):
        pages = []
        for id in ids:
            obj = self.get_one(id)
            self.enable_page(obj)
            pages.append(obj.name)

        flash(u'成功启用以下的页面解析设置.<br />%s' % ', '.join(pages), 'success')

    @action('disable', u'停用')
    def b_disable_conf(self, ids):
        pages = []
        for id in ids:
            obj = self.get_one(id)
            self.disable_page(obj)
            pages.append(obj.name)

        flash(u'成功停用以下的页面解析设置.<br />%s' % ', '.join(pages), 'success')

    @expose('/check/', methods=['POST'])
    def check(self):
        data = get_form_data()
        form = self._create_form_class(data)
        # print dir(form)
        d = {}
        for f in form._fields:
            d[f] = getattr(form, f).data

        # rules = []
        if 'link_rules' in d:
            for rule in d['link_rules']:
                # print(rule)
                page = rule.pop('page')
                rule['page'] = page.alias
                if 'allows' in rule and rule['allows']:
                    rule['allows'] = rule['allows'].strip().split('\n')
                if 'denies' in rule and rule['denies']:
                    rule['denies'] = rule['denies'].strip().split('\n')
            # rules.append('rule')
        return json.dumps(self.test_conf(d)), 200, {'Content-Type': 'application/json'}

    def test_conf(self, conf):
        import html as cgi
        import traceback
        from kombu.utils.encoding import str_to_bytes
        from yunduo.utils import merge, pprint
        from yunduo.errors import DenyError
        from yunduo.resource import get_connection
        from yunduo.code import compile, get_function
        from yunduo.downloader.models import Response
        from requests.utils import dict_from_cookiejar
        from yunduo.downloader import download
        from yunduo.parser.htmlextractor import Link, Extractor, ItemResult

        messages = []
        debugs = []

        try:
            test_conf = conf.pop('test_conf')
            # print test_conf
            if test_conf:
                conf = merge(conf, test_conf)
        except Exception:
            traceback.print_exc()

        try:

            url = conf.pop('test_url', None)
            html = conf.pop('test_html', None)
            if html:
                resp = Response()
                # print type(html)
                if url:
                    resp.url = url
                resp._content = str_to_bytes(html)
                resp.status_code = 200
                resp.reason = 'OK From String'
            else:
                before_request = conf.get('before_request')
                after_response = conf.get('after_response')

                if before_request or after_response:
                    info = {
                        'project': current_project.alias
                    }
                    env = {
                        # 'send_notify': _send_notify,
                        # 'Link': Link,
                        # 'Extractor': Extractor,
                        # 'ItemResult': ItemResult,
                        'get_connection': get_connection,
                        'DenyError': DenyError,
                        # 'crawl': _crawl,
                        # 'download': _download,
                        'dprint': lambda *args, **kw: None,
                        'environ': info.copy()
                    }
                    if before_request:
                        conf['before_request'] = get_function(before_request, 'before_request', env)

                    if after_response:
                        conf['after_response'] = get_function(after_response, 'after_response', env)
                # print('download conf = ', url, conf)
                resp = download(url, **conf)
        except Exception:
            exc = traceback.format_exc()
            return {'messages': [u'抓取失败 %s' % cgi.escape(exc)]}

        if not resp or resp.status_code not in (200, 222):
            # print resp.request.headers
            return {'messages': [u'抓取失败，返回: %s < %s > size=%s' % (resp.status_code, resp.reason, len(resp.content))]}

        messages.append(u'下载成功：<br />code=%s size=%s<br />%s' % (resp.status_code, len(resp.content), resp.url))

        links = []

        def _crawl(page, url=None, **kw):
            if isinstance(page, Link):
                links.append(page)
            elif url:
                lnk = Link(page, url, **kw)
                links.append(lnk)

        def _download(url, **kw):
            ic = kw.pop('follow_cookie', True)
            if ic:
                cks = dict_from_cookiejar(resp.cookies)
                cookies = kw.setdefault('cookies', {})
                if cks:
                    cks.update(cookies)
                    kw['cookies'] = cks

            if resp.request and resp.request.proxies:
                kw['proxies'] = resp.request.proxies

            hdrs = kw.setdefault('headers', {})
            # if resp.request:
            #     hs = dict(resp.request.headers)
            #     hs.update(hdrs)
            #     kw['headers'] = hs
            hdrs.setdefault('Referer', resp.url)
            return download(url, **kw)

        def dprint(*msg):
            k = []
            for m in msg:
                k.append(cgi.escape(repr(m)))
            debugs.append(' &nbsp; '.join(k))

        def _compile(code, **env):
            g = {}
            g.update(env)
            return compile(code, **g)

        item_type = conf.get('item_type')
        item_fields = conf.get('item_fields')
        item_pycode = conf.get('item_pycode')
        link_type = conf.get('link_type')
        link_rules = conf.get('link_rules')
        link_pycode = conf.get('link_pycode')
        # _meta = conf.pop('meta', None) or {}
        # _meta.update(resp.meta)
        # env = {
        #     'Link': Link,
        #     'Extractor': Extractor,
        #     'ItemResult': ItemResult,
        #     # 'BlockedError': BlockedError,
        #     'crawl': _crawl,
        #     'download': _download,
        #     'dprint': dprint,
        #     'ENV': {
        #         'conf': conf,
        #         'meta': _meta
        #     }
        # }

        env = {
            # 'send_notify': _send_notify,
            'Link': Link,
            'Extractor': Extractor,
            'ItemResult': ItemResult,
            # 'BlockedError': BlockedError,
            'crawl': _crawl,
            'download': _download,
            'dprint': dprint,
            'environ': {
                'project': current_project.alias,
                'job': None,
                'page': conf['alias'],
                'url': url,
                'batch_id': None,
                'meta': None
            }
        }


        exor = None
        encoding = conf.get('encoding')
        if not encoding:
            encoding = None

        if not item_type and not link_type:
            messages.append('<span style="color:red">请先设置链接抽取和内容解析设置</span>')
        #
        data = None
        try:
            if item_type == 'conf' and item_fields:
                exor = Extractor(resp, encoding)
                data = exor.extract_items(item_fields)
                # data = self.parse_item_by_conf(resp, items['fields'])
            elif item_type == 'code' and item_pycode:
                genv = _compile(item_pycode, **env)
                extr_items = genv.get('extract_items')
                conf_items = genv.get('conf_items')
                if extr_items and callable(extr_items):
                    data = extr_items(resp)
                elif conf_items:
                    exor = Extractor(resp, encoding)
                    data = exor.extract_items(conf_items)
            elif item_type:
                messages.append('<span style="color:red">内容解析设置不正确</span>')
        except Exception:
            # stat_data['code_910'] = 1
            # self.logger.exception(u'解析字段错误 %s %s %s', proj, page, resp.url)
            ex = traceback.format_exc()
            messages.append('<span style="color:red">抽取内容失败：</span>%s' % cgi.escape(ex))
        else:
            if data:
                if isinstance(data, ItemResult):
                    data, missing, miss_rate = data
                else:
                    missing, miss_rate = None, None

                if isinstance(data, dict):
                    item_num = 1
                    data = [data]
                else:
                    item_num = len(data)
                messages.append('<b>共抽取出数据 %s 条</b>' % item_num)
                if missing:
                    messages.append('数据缺失字段 %s 缺失率 %s' % (missing, miss_rate))

                for item in data:
                    messages.append(pprint.pformat(item, indent=4))

                # self.save_item(proj, page, items['datastore'], data, missing)

            if item_type and not data:
                # stat_data['code_911'] = 1
                # self.logger.warning(u'抽取不到数据 %s %s %s', proj, page, resp.url)
                messages.append('<span style="color:red">抽取不到数据</span>')
        #
        urls = None
        # print links
        try:
            # print 'link_rules', link_rules
            if link_type == 'conf' and link_rules:
                if not exor:
                    exor = Extractor(resp, encoding)
                urls = exor.extract_links(link_rules)
                # urls = self.parse_link_by_conf(resp, links['rules'])
            elif link_type == 'code' and link_pycode:
                genv = compile(link_pycode, **env)
                extr_links = genv.get('extract_links')
                conf_links = genv.get('conf_links')
                if extr_links and callable(extr_links):
                    urls = extr_links(resp)
                elif conf_links:
                    if not exor:
                        exor = Extractor(resp, encoding)
                    urls = exor.extract_links(conf_links)
            elif link_type:
                messages.append('<span style="color:red">链接抽取设置不正确</span>')
        except Exception:
            # stat_data['code_920'] = 1
            # self.logger.exception(u'抽取链接错误 %s %s %s', proj, page, resp.url)
            ex = traceback.format_exc()
            messages.append('<span style="color:red">抽取链接失败</span>：%s' % cgi.escape(ex))

        if urls:
            links.extend(urls)

        if links:
            messages.append('<b>抽取的链接 共 %s 条</b>' % len(links))
            for link in links:
                messages.append('%s' % link)
        elif link_type:
            messages.append('<span style="color:red">没有抽取出链接</span>')

        return {
            'messages': messages,
            'debugs': debugs
        }


