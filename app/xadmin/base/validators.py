
from wtforms import validators, ValidationError


class Unique(object):

    def __init__(self, model, column, message=None):
        self.model = model
        self.column = column
        self.message = message

    def __call__(self, form, field):
        # databases allow multiple NULL values for unique columns
        if field.data is None:
            return

        filters = {self.column: field.data}
        obj = self.model.objects.filter(**filters).first()

        _obj = getattr(form, '_obj', None)
        if obj and (_obj is None or (_obj and not (form._obj == obj))):
            if self.message is None:
                self.message = field.gettext('Already exists.')
            raise ValidationError(self.message)


class UniqueWith(object):

    def __init__(self, model, column, with_columns, message=None):
        self.model = model
        self.column = column
        self.with_columns = with_columns
        self.message = message

    def __call__(self, form, field):
        # databases allow multiple NULL values for unique columns
        if field.data is None:
            return

        filters = {self.column: field.data}
        for column in self.with_columns:
            with_field = form[column]
            filters[column] = with_field.data

        obj = self.model.objects.filter(**filters).first()
        _obj = getattr(form, '_obj', None)
        # print('UniqueWith', filters, obj, form._obj, type(field))
        # print('UniqueWith => ', (obj and _obj is None) or (_obj and form._obj == obj))

        if obj and (_obj is None or (_obj and not (form._obj == obj))):
            if self.message is None:
                self.message = field.gettext('Already exists.')
            # print('-----------------------------------')
            raise ValidationError(self.message)


class ConditionRequired(object):

    def __init__(self, judegeFunc, message=None):
        self.judegeFunc = judegeFunc
        self.message = message

    def __call__(self, form, field):
        if self.judegeFunc(form, field):
            if not field.data or isinstance(field.data, validators.string_types) and not field.data.strip():
                if self.message is None:
                    message = field.gettext('This field is required.')
                else:
                    message = self.message

                field.errors[:] = []
                raise validators.StopValidation(message)


