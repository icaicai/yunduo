# coding=utf8

from jinja2 import Markup
from flask_admin import helpers
from flask_admin.form import rules


class Column(rules.BaseRule):

    def __init__(self, *rules, **kw):
        super(Column, self).__init__()
        self.rules = rules
        self.prefix = kw.get('prefix', None)
        self.width = kw.get('width', None)
        # self.col = 'col-md-6'

    def configure(self, rule_set, parent):
        self.rules = rule_set.configure_rules(self.rules, self)
        return super(Column, self).configure(rule_set, parent)

    @property
    def visible_fields(self):
        visible_fields = []
        for rule in self.rules:
            for field in rule.visible_fields:
                visible_fields.append(field)
        return visible_fields

    def __iter__(self):
        for r in self.rules:
            yield r

    def __call__(self, form, form_opts=None, field_args={}, **kw):
        result = []

        for r in self.rules:
            result.append(r(form, form_opts, field_args))
        prefix = self.prefix or kw.get('prefix', '')
        width = self.width or kw.get('width', '')
        return Markup('<div class="%s%s">%s</div>' % (prefix, width, ''.join(result)))


class Row(rules.BaseRule):

    def __init__(self, *columns, **kw):
        super(Row, self).__init__()
        self.columns = columns
        self.prefix = kw.get('prefix', 'col-md-')

    def configure(self, rule_set, parent):
        self.columns = rule_set.configure_rules(self.columns, self)
        return super(Row, self).configure(rule_set, parent)

    @property
    def visible_fields(self):
        visible_fields = []
        for rule in self.columns:
            for field in rule.visible_fields:
                visible_fields.append(field)
        return visible_fields

    def __call__(self, form, form_opts=None, field_args={}):
        s = []
        cs = [c.width for c in self.columns if c.width is not None]
        # print('Row => ', cs)
        k = (len(self.columns) - len(cs))
        if k > 0:
            wid = int((12 - sum(cs)) / k)
        else:
            wid = 0
        kw = {
            'prefix': self.prefix,
            'width': wid
        }
        for column in self.columns:
            s.append(column(form, form_opts, field_args, **kw))

        return Markup('<div class="row">%s</div>' % ''.join(s))


class Box(rules.Container):
    """docstring for Tab"""
    def __init__(self, title, child_rule, **kwargs):
        kwargs['title'] = title
        super(Box, self).__init__('lib.box', child_rule, **kwargs)

    # def __call__(self, form, form_opts=None, field_args={}):
    #     context = helpers.get_render_ctx()
    #
    #     def caller(**kwargs):
    #         return context.call(self.child_rule, form, form_opts, kwargs)
    #
    #     args = dict(field_args)
    #     args['caller'] = caller
    #
    #     return super(Container, self).__call__(form, form_opts, args)


# collapse
# title
# class

