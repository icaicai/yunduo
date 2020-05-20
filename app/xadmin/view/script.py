# coding=utf8

from datetime import datetime
from flask import current_app, flash, jsonify
from flask_admin import expose
from flask_admin.actions import action
from flask_admin.contrib.mongoengine.form import get_form
from flask_admin.form import FormOpts, rules
from flask_admin.babel import gettext
# from connections import redis_conf
from yunduo.conf import xconf
from xadmin.view.base import BaseView
from xadmin.utils.format import date_format, map_format, edit_link_format
from xadmin.constant import STATUS_DISABLE, STATUS_ENABLE
# from xspider.app import app as celery_app
from xadmin.helpers import current_project


# Customized admin views
class ScriptView(BaseView):
    inject_current_project = True
    column_list = ['name', 'alias', 'type', 'status', 'updated', 'published']
    column_filters = ['name', 'alias']

    column_labels = {
        'project': u'所属项目',
        'name': u'名称',
        'alias': u'别名',
        'tags': u'类型',
        'status': u'状态',
        'tags': u'标签',
        'created': u'新增时间',
        'updated': u'更新时间',
        'published': u'发布时间'

    }

    column_searchable_list = ('name', 'alias')
    column_formatters = {
        'name': edit_link_format,
        'status': map_format({STATUS_ENABLE: u'启用', STATUS_DISABLE: u'停用'}),
        # 'type': map_format({0: u'通用', 1: u'存储', 2: u'告警'}),
        'created': date_format,
        'updated': date_format,
        'published': date_format,
    }
    # form_ajax_refs = {
    #     'entry_page': {
    #         'model': 'Page',
    #         'fields': ('name',)
    #     }
    # }

    form_rules = [
        'project', 'name', 'alias', 'tags', 'pycode'
    ]

    form_args = {
        'project': {
            'readonly': 'readonly'
        }
    }

    form_widget_args = {
        'pycode': {
            'data-role': 'editor',
            'data-lang': 'python',
            'data-min-lines': 30,
            'data-max-lines': 30
        }
    }

    def _refresh_forms_cache(self):
        super(ScriptView, self)._refresh_forms_cache()
        self._form_simple_create_class = get_form(
            self.model, self.model_form_converter(self), base_class=self.form_base_class,
            only=('project', 'name', 'alias'), exclude=self.form_excluded_columns,
            field_args=self.form_args, extra_fields=self.form_extra_fields)

    def _refresh_form_rules_cache(self):
        super(ScriptView, self)._refresh_form_rules_cache()
        self._form_simple_create_rules = rules.RuleSet(self, ['project', 'name', 'alias'])

    def create_simple_form(self, obj=None):
        return self.create_form(obj, self._form_simple_create_class)

    def enable_script(self, obj):
        # if obj.status == STATUS_ENABLE:
        #     return False

        project = obj.project.alias if obj.project else None
        xconf.set_script(project, obj.alias, obj.to_conf())
        obj.status = STATUS_ENABLE
        obj.published = datetime.now()
        obj.save()
        self.logger.info(u'启用脚本 %s', obj.name, extra={'project': project, 'script': obj.alias})
        return True

    def disable_script(self, obj):
        # if obj.status == STATUS_DISABLE:
        #     return False

        project = obj.project.alias if obj.project else None
        xconf.del_script(project, obj.alias)
        obj.status = STATUS_DISABLE
        obj.save()
        self.logger.info(u'停用脚本 %s', obj.name, extra={'project': project, 'script': obj.alias})
        return True

    @action('enable', u'启用')
    def a_enable_conf(self, ids):
        scripts = []
        for id in ids:
            obj = self.get_one(id)
            self.enable_script(obj)
            scripts.append(obj.name)

        flash(u'成功启用以下脚本.<br />%s' % ', '.join(scripts), 'success')

    @action('stop', u'停用')
    def c_disable_conf(self, ids):
        scripts = []
        for id in ids:
            obj = self.get_one(id)
            self.disable_script(obj)
            scripts.append(obj.name)

        self.clear_script(scripts)
        flash(u'成功停用以下脚本.<br />%s' % ', '.join(scripts), 'success')

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

    def clear_script(self, scripts):
        from xspider.app import app
        for script in scripts:
            app.control.clear_script(current_project.alias, script)
