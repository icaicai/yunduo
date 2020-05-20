# coding=utf8

import six

from math import ceil
from datetime import datetime
from wtforms import form
from werkzeug.datastructures import ImmutableMultiDict
from pymongo import DESCENDING, ASCENDING
from flask import (Response, request, current_app, redirect, url_for, flash, abort, json, get_flashed_messages)
from flask_security import current_user
from flask_admin.base import expose
from flask_admin.form import FormOpts
from flask_admin.model import template
# from flask_admin.contrib.mongoengine import ModelView
from flask_admin.contrib import mongoengine, pymongo
from flask_admin.babel import gettext
from flask_admin.helpers import (get_redirect_target, flash_errors, get_form_data)
from flask_admin._compat import iteritems, as_unicode
from flask_admin.model.base import ViewArgs
from flask_admin.model.helpers import get_mdict_item_or_list

from xadmin.base.form import CustomModelConverter
from xadmin.base.ajax import process_ajax_references, create_ajax_loader
from xadmin.helpers import current_project


class BaseMixin(object):

    @property
    def logger(self):
        return current_app.logger

    def _get_endpoint(self, endpoint):
        if endpoint:
            return endpoint

        endpoint = self.__class__.__name__.lower()
        if endpoint.endswith('view') and endpoint != 'view':
            endpoint = endpoint[:-4]
        return endpoint

    # URL generation helpers
    def _get_list_filter_args(self):
        if self._filters:
            filters = []

            for n in request.args:
                if not n.startswith('flt'):
                    continue

                if '_' not in n:
                    continue

                pos, key = n[3:].split('_', 1)

                if key in self._filter_args:
                    idx, flt = self._filter_args[key]
                    value = request.args[n]
                    if value.strip() == '':
                        continue

                    if flt.validate(value):
                        filters.append((pos, (idx, as_unicode(flt.name), value)))
                    else:
                        flash(gettext('Invalid Filter Value: %(value)s', value=value), 'error')
            # Sort filters
            return [v[1] for v in sorted(filters, key=lambda n: n[0])]
        return None

    # def _get_filters(self, filters):
    #     kwargs = super()._get_filters(filters)
    #     model = getattr(self, 'model', None)
    #     if current_project and model and 'project' in model._fields:
    #         kwargs.setdefault('project', current_project)
    #     return kwargs

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('superuser'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class MongoView(BaseMixin, pymongo.ModelView):
    inject_current_project = True
    inject_project_field = 'meta.project'

    can_create = False
    can_edit = False
    can_delete = False

    form = form.Form

    collection = None

    def __init__(self, name=None, category=None, endpoint=None, url=None,
                 menu_class_name=None, menu_icon_type=None, menu_icon_value=None):

        if name is None:
            name = self._prettify_name(self.__class__.__name__)
        if not endpoint:
            endpoint = self.__class__.__name__.lower()
            if endpoint.endswith('view') and endpoint != 'view':
                endpoint = endpoint[:-4]

        self.initialize()
        super(MongoView, self).__init__(self.collection, name, category, endpoint, url,
                                        menu_class_name=menu_class_name,
                                        menu_icon_type=menu_icon_type,
                                        menu_icon_value=menu_icon_value)

    def initialize(self):
        pass

    def _get_field_value(self, model, name):
        if '.' in name:
            ns = name.split('.')
            vl = model
            for name in ns:
                try:
                    vl = vl.get(name)
                except Exception:
                    return None
            return vl
        else:
            return model.get(name)

    def get_list(self, page, sort_column, sort_desc, search, filters,
                 execute=True, page_size=None):

        query = {}
        if self.inject_current_project and current_project:
            query[self.inject_project_field] = current_project.alias

        # Filters
        if self._filters:
            data = []

            for flt, flt_name, value in filters:
                f = self._filters[flt]
                data = f.apply(data, value)

            if data:
                if len(data) == 1:
                    query = data[0]
                else:
                    query['$and'] = data

        # Search
        if self._search_supported and search:
            query = self._search(query, search)

        # Get count
        count = self.coll.find(query).count() if not self.simple_list_pager else None

        # Sorting
        sort_by = None

        if sort_column:
            sort_by = [(sort_column, DESCENDING if sort_desc else ASCENDING)]
        else:
            order = self._get_default_order()

            if order:
                sort_by = [(order[0], DESCENDING if order[1] else ASCENDING)]

        # Pagination
        if page_size is None:
            page_size = self.page_size

        skip = 0

        if page and page_size:
            skip = page * page_size

        results = self.coll.find(query, sort=sort_by, skip=skip, limit=page_size)

        if execute:
            results = list(results)

        return count, results


class BaseView(BaseMixin, mongoengine.ModelView):

    inject_current_project = False

    model_form_converter = CustomModelConverter

    def _index_render_kw(self):
        return {}

    def _validate_form_class(self, ruleset, form_class, remove_missing=False):
        return super(BaseView, self)._validate_form_class(ruleset, form_class, remove_missing)

    def _validate_form_instance(self, ruleset, form, remove_missing=False):
        return super(BaseView, self)._validate_form_instance(ruleset, form, remove_missing)

    def _process_ajax_references(self):
        references = super(BaseView, self)._process_ajax_references()
        return process_ajax_references(references, self)

    def _create_ajax_loader(self, name, opts):
        return create_ajax_loader(self.model, name, name, opts)

    def get_query(self):
        query = self.model.objects
        if self.inject_current_project and current_project and 'project' in self.model._fields:
            query = query.filter(project=current_project.id)
        return query

    def create_form(self, obj=None, klass=None):
        data = get_form_data()
        if not data:
            params = {}
            active_filters = self._get_list_filter_args()
            if active_filters:
                for i, flt in enumerate(active_filters):
                    key = self.column_filters[flt[0]]
                    params[key] = flt[2]

            if self.inject_current_project and current_project and 'project' in self.model._fields:
                params.setdefault('project', current_project.id)

            data = ImmutableMultiDict(params)

        if klass is None:
            klass = self._create_form_class

        form = klass(data, obj=obj)
        return form

    def is_action_allowed(self, name):
        # Check delete action permission
        if name == 'delete':
            return False

        return super(BaseView, self).is_action_allowed(name)

    def get_list_row_actions(self):

        actions = []

        if self.can_view_details:
            if self.details_modal:
                actions.append(template.ViewPopupRowAction())
            else:
                actions.append(template.ViewRowAction())

        if self.can_edit:
            if self.edit_modal:
                actions.append(template.EditPopupRowAction())
            else:
                actions.append(template.EditRowAction())

        if self.can_delete:
            actions.append(template.DeleteRowAction())

        return (self.column_extra_row_actions or []) + actions

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.created = datetime.now()
        else:
            model.updated = datetime.now()

    def redirect(self, url):
        print('==========Redirect to %s ' % url)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            scripts = []

            if url.startswith(self.get_url('.index_view')):
                scripts.append('$("#modal_window_fa").modal("hide");')
                # scripts.append('$("#list-grid-view").bootgrid("reload");')

                messages = get_flashed_messages(True)
                if messages:
                    iconm = {'message': 'icon fa fa-info', 'warn': 'icon fa fa-warning',
                             'warning': 'icon fa fa-warning', 'error': 'icon fa fa-ban',
                             'success': 'icon fa fa-check'}
                    mapping = {'message': 'info', 'error': 'danger'}
                    tmpl = u"$.notify({message: '%s', icon: '%s'}, {type: '%s'});"
                    for cate, msg in messages:
                        scripts.append(tmpl % (msg, iconm.get(cate, cate), mapping.get(cate, cate)))
            else:
                scripts.append('location.href="%s"' % (url,))
            return u'<script language="javascript">%s</script>' % ('\n'.join(scripts), )
        else:
            return redirect(url)

    # Views
    @expose('/')
    def index_view(self):
        # print 'index_view', self._filter_args
        if self.can_delete:
            delete_form = self.delete_form()
        else:
            delete_form = None

        # Grab parameters from URL
        view_args = self._get_list_extra_args()

        # Map column index to column name
        sort_column = request.args.get('sort', None)
        # print self._list_columns, self._sortable_columns
        if sort_column and sort_column not in self._sortable_columns:
            sort_column = None
        # if sort_column is not None:
        #     sort_column = sort_column[0]

        # Get page size
        page_size = view_args.page_size or self.page_size

        # Get count and data
        count, data = self.get_list(view_args.page, sort_column, view_args.sort_desc,
                                    view_args.search, view_args.filters, page_size=page_size)

        # if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        #     rows = []
        #     for row in data:
        #         r = {}
        #         r[self.scaffold_pk()] = str(self.get_pk_value(row))
        #         for c, name in self._list_columns:
        #             r[c] = self.get_list_value(None, row, c)
        #         rows.append(r)

        #     return Response(json.dumps({
        #         "current": view_args.page + 1,
        #         "rowCount": page_size,
        #         "rows": rows,
        #         "total": count
        #     }), mimetype='application/json')

        list_forms = {}
        if self.column_editable_list:
            for row in data:
                list_forms[self.get_pk_value(row)] = self.list_form(obj=row)

        # Calculate number of pages
        if count is not None and page_size:
            num_pages = int(ceil(count / float(page_size)))
        elif not page_size:
            num_pages = 0  # hide pager for unlimited page_size
        else:
            num_pages = None  # use simple pager

        # Various URL generation helpers
        def pager_url(p):
            # Do not add page number if it is first page
            if p == 0:
                p = None

            return self._get_list_url(view_args.clone(page=p))

        def sort_url(column, invert=False, desc=None):
            if not desc and invert and not view_args.sort_desc:
                desc = 1

            return self._get_list_url(view_args.clone(sort=column, sort_desc=desc))

        def page_size_url(s):
            if not s:
                s = self.page_size

            return self._get_list_url(view_args.clone(page_size=s))

        # Actions
        actions, actions_confirmation = self.get_actions_list()
        if actions:
            action_form = self.action_form()
        else:
            action_form = None

        clear_search_url = self._get_list_url(view_args.clone(page=0,
                                                              sort=view_args.sort,
                                                              sort_desc=view_args.sort_desc,
                                                              search=None,
                                                              filters=None))

        render_kw = self._index_render_kw()

        return self.render(
            self.list_template,
            data=data,
            list_forms=list_forms,
            delete_form=delete_form,
            action_form=action_form,
            # List
            list_columns=self._list_columns,
            sortable_columns=self._sortable_columns,
            editable_columns=self.column_editable_list,
            list_row_actions=self.get_list_row_actions(),
            # Pagination
            count=count,
            pager_url=pager_url,
            num_pages=num_pages,
            can_set_page_size=self.can_set_page_size,
            page_size_url=page_size_url,
            page=view_args.page,
            page_size=page_size,
            default_page_size=self.page_size,
            # Sorting
            sort_column=view_args.sort,
            sort_desc=view_args.sort_desc,
            sort_url=sort_url,
            # Search
            search_supported=self._search_supported,
            clear_search_url=clear_search_url,
            search=view_args.search,
            # Filters
            filters=self._filters,
            filter_groups=self._get_filter_groups(),
            active_filters=view_args.filters,
            filter_args=self._get_filters(view_args.filters),
            # Actions
            actions=actions,
            actions_confirmation=actions_confirmation,
            # Misc
            enumerate=enumerate,
            get_pk_value=self.get_pk_value,
            get_value=self.get_list_value,
            return_url=self._get_list_url(view_args),
            **render_kw
        )

    @expose('/new/', methods=('GET', 'POST'))
    def create_view(self):
        """
            Create model view
        """
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not self.can_create:
            return self.redirect(return_url)

        form = self.create_form()
        if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:
            self._validate_form_instance(ruleset=self._form_create_rules, form=form)

        if self.validate_form(form):
            # in versions 1.1.0 and before, this returns a boolean
            # in later versions, this is the model itself
            model = self.create_model(form)
            if model:
                flash(gettext('Record was successfully created.'), 'success')
                if '_add_another' in request.form:
                    return self.redirect(request.url)
                elif '_continue_editing' in request.form:
                    # if we have a valid model, try to go to the edit view
                    if model is not True:
                        url = self.get_url('.edit_view', id=self.get_pk_value(model), url=return_url)
                    else:
                        url = return_url
                    return self.redirect(url)
                else:
                    # save button
                    return self.redirect(self.get_save_return_url(model, is_created=True))

        form_opts = FormOpts(widget_args=self.form_widget_args,
                             form_rules=self._form_create_rules)

        if self.create_modal and request.args.get('modal'):
            template = self.create_modal_template
        else:
            template = self.create_template

        return self.render(template,
                           form=form,
                           form_opts=form_opts,
                           return_url=return_url)

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        """
            Edit model view
        """
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not self.can_edit:
            return self.redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return self.redirect(return_url)

        model = self.get_one(id)

        if model is None:
            flash(gettext('Record does not exist.'), 'error')
            return self.redirect(return_url)

        form = self.edit_form(obj=model)
        if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:
            self._validate_form_instance(ruleset=self._form_edit_rules, form=form)

        if self.validate_form(form):
            if self.update_model(form, model):
                flash(gettext('Record was successfully saved.'), 'success')
                if '_add_another' in request.form:
                    return self.redirect(self.get_url('.create_view', url=return_url))
                elif '_continue_editing' in request.form:
                    return self.redirect(request.url)
                else:
                    # save button
                    return self.redirect(self.get_save_return_url(model, is_created=False))

        if request.method == 'GET' or form.errors:
            self.on_form_prefill(form, id)

        form_opts = FormOpts(widget_args=self.form_widget_args,
                             form_rules=self._form_edit_rules)

        if self.edit_modal and request.args.get('modal'):
            template = self.edit_modal_template
        else:
            template = self.edit_template

        return self.render(template,
                           model=model,
                           form=form,
                           form_opts=form_opts,
                           return_url=return_url)

    @expose('/details/')
    def details_view(self):
        """
            Details model view
        """
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not self.can_view_details:
            return self.redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return self.redirect(return_url)

        model = self.get_one(id)

        if model is None:
            flash(gettext('Record does not exist.'), 'error')
            return self.redirect(return_url)

        if self.details_modal and request.args.get('modal'):
            template = self.details_modal_template
        else:
            template = self.details_template

        return self.render(template,
                           model=model,
                           details_columns=self._details_columns,
                           get_value=self.get_list_value,
                           return_url=return_url)

    @expose('/delete/', methods=('POST',))
    def delete_view(self):
        """
            Delete model view. Only POST method is allowed.
        """
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not self.can_delete:
            return self.redirect(return_url)

        form = self.delete_form()

        if self.validate_form(form):
            # id is InputRequired()
            id = form.id.data

            model = self.get_one(id)

            if model is None:
                flash(gettext('Record does not exist.'), 'error')
                return self.redirect(return_url)

            # message is flashed from within delete_model if it fails
            if self.delete_model(model):
                flash(gettext('Record was successfully deleted.'), 'success')
                return self.redirect(return_url)
        else:
            flash_errors(form, message='Failed to delete record. %(error)s')

        return self.redirect(return_url)

    # @expose('/ajax/lookup/')
    # def ajax_lookup(self):
    #     name = request.args.get('name')
    #     query = request.args.get('query')
    #     offset = request.args.get('offset', type=int)
    #     limit = request.args.get('limit', 10, type=int)

    #     loader = self._form_ajax_refs.get(name)

    #     if not loader:
    #         abort(404)

    #     print request.args.to_dict()
    #     # if loader.model is self.model:
    #     #     query = loader.model.objects
    #     #     if self._filters:
    #     #         filters = self._get_list_filter_args()
    #     #         for flt, flt_name, value in filters:
    #     #             f = self._filters[flt]
    #     #             query = f.apply(query, f.clean(value))
    #     # else:
    #     #     query = loader.model.objects

    #     # filter_args = self._get_filters()
    #     # if filter_args:
    #     #     query = query.filter(**filter_args)
    #     data = [loader.format(m) for m in loader.get_list(query, offset, limit)]
    #     return Response(json.dumps(data), mimetype='application/json')

    @expose('/ajax/lookup/')
    def ajax_lookup(self):
        name = request.args.get('name', '__self__')
        term = request.args.get('term')
        offset = request.args.get('offset', type=int)
        limit = request.args.get('limit', 10, type=int)
        # print(self._form_ajax_refs)
        loader = self._form_ajax_refs.get(name)

        if not loader:
            abort(404)

        # query = loader.model.objects
        # args = request.args.to_dict()
        params = self.get_extra_filters()
        # if params:
        #     query = query.filter(**params)
        if self.inject_current_project and current_project and 'project' in loader.model._fields:
            params.setdefault('project', current_project.id)

        data = [loader.format(m) for m in loader.get_list(term, offset, limit, filters=params)]
        return Response(json.dumps(data), mimetype='application/json')

    def get_extra_filters(self):
        params = {}
        for key, val in request.args.items():
            if key.startswith('filter-') and val:
                fld = key[7:]
                params[fld] = val

        return params
