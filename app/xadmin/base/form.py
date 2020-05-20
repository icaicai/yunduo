# coding=utf8

import json
from wtforms import widgets
from wtforms import fields as wtf_fields, validators
from wtforms.widgets.core import html_params, HTMLString
from mongoengine import ReferenceField, ListField
from flask_mongoengine.wtf import orm, fields
from flask_admin.model.fields import InlineFieldList, AjaxSelectField
from flask_admin.contrib.mongoengine import form
from flask_admin import form as admin_form
from flask_admin import babel
from flask_admin._backwards import get_property
from flask_admin.model.helpers import prettify_name
from flask_admin.model.form import FieldPlaceholder
from .validators import Unique, UniqueWith


class StaticInputWidget(widgets.Select):

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        if self.multiple:
            kwargs['multiple'] = True

        # addition_fields = kwargs.pop('addition_fields', None)
        val, label = None, None
        for val, label, selected in field.iter_choices():
            # html.append(self.render_option(val, label, selected))
            if selected:
                break
        # print val, label, selected, type(val), type(label), type(selected)
        kwargs['value'] = val
        html = [u'<input type="hidden" %s>' % html_params(name=field.name, **kwargs)]
        # try:
        #     if label.__class__.__name__ == 'Project':
        #         html.append(u'<input type="hidden" %s>' % html_params(name='project_type', id='project_type', value=label.type))
        # except Exception:
        #     pass

        # html.append(u'<label class="control-label">%s</label>' % label)
        # html.append(u'<label class="control-label">%s</label>' % label)
        html.append(u'<p class="form-control-static">%s</p>' % label)
        return HTMLString(u''.join(html))


class DictField(fields.DictField):

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        else:
            return self.data and str(json.dumps(self.data, ensure_ascii=False, indent=2)) or u''

    def process_formdata(self, value):
        if not value:
            self.data = {}
        else:
            super(DictField, self).process_formdata(value)


class CustomModelConverter(form.CustomModelConverter):

    def _get_label(self, field, field_args):
        name = field.name
        if field_args and 'label' in field_args:
            return field_args['label']

        column_labels = get_property(self.view, 'column_labels', 'rename_columns')

        if column_labels:
            return column_labels.get(name)

        return getattr(field, 'verbose_name', None)

    def convert(self, model, field, field_args):
        # Check if it is overridden field
        if isinstance(field, FieldPlaceholder):
            return form.recreate_field(field.field)

        kwargs = {
            'label': self._get_label(field, field_args),
            'description': getattr(field, 'help_text', ''),
            'validators': [],
            'filters': [],
            'default': field.default,
            # '_translations': babel
        }

        if field_args:
            kwargs.update(field_args)

        if kwargs['validators']:
            # Create a copy of the list since we will be modifying it.
            kwargs['validators'] = list(kwargs['validators'])

        if field.required:
            kwargs['validators'].append(validators.InputRequired())
        elif not isinstance(field, ListField):
            kwargs['validators'].append(validators.Optional())

        if field.unique and not field.unique_with:
            kwargs['validators'].append(Unique(model, field.name))

        if field.unique_with:
            # print field.unique_with, '<<<<<<<<<<<', field.unique
            kwargs['validators'].append(UniqueWith(model, field.name, field.unique_with))

        ftype = type(field).__name__
        override = self._get_field_override(field.name)

        # Check choices
        form_choices = getattr(self.view, 'form_choices', None)
        #
        # if mapper.class_ == self.view.model and form_choices:
        #     choices = form_choices.get(prop.key)
        #     if choices:
        #         return form.Select2Field(
        #             choices=choices,
        #             allow_blank=column.nullable,
        #             **kwargs
        #         )

        choices = field.choices
        if form_choices and field.name in form_choices:
            choices = form_choices[field.name]

        if choices:
            kwargs['choices'] = list(self._convert_choices(field.choices))
            if ftype in self.converters:
                kwargs["coerce"] = self.coerce(ftype)
            if kwargs.pop('radio', False):
                return wtf_fields.RadioField(**kwargs)

            if not override:
                if kwargs.pop('multiple', False):
                    return wtf_fields.SelectMultipleField(**kwargs)
                return wtf_fields.SelectField(**kwargs)

        if hasattr(field, 'to_form_field'):
            return field.to_form_field(model, kwargs)

        if override:
            return override(**kwargs)

        if ftype in self.converters:
            return self.converters[ftype](model, field, kwargs)

    @orm.converts('ReferenceField')
    def conv_Reference(self, model, field, kwargs):
        kwargs['allow_blank'] = not field.required

        loader = getattr(self.view, '_form_ajax_refs', {}).get(field.name)
        if loader:
            return AjaxSelectField(loader, **kwargs)

        readonly = kwargs.pop('readonly', False)
        if readonly:
            kwargs['widget'] = StaticInputWidget()
        else:
            kwargs['widget'] = admin_form.Select2Widget()
        # print '====CustomModelConverter====', kwargs

        return orm.ModelConverter.conv_Reference(self, model, field, kwargs)

    @orm.converts('DictField')
    def conv_Dict(self, model, field, kwargs):
        return DictField(**kwargs)
