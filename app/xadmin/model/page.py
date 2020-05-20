# coding=utf8

from datetime import datetime
from .base import db, Document


class LinkRule(db.EmbeddedDocument):
    # _form_subdocuments = {
    #     'page': 'Page'
    # }
    page = db.ReferenceField('Page', required=True)
    # page_name = db.StringField(required=True)
    # page = db.StringField(required=True, min_length=1, max_length=150)
    sel_type = db.StringField(required=True, default='css', choices=[('css', 'CSS'), ('xpath', 'XPath')])
    selector = db.StringField(required=True, min_length=1, max_length=255)
    df_enable = db.BooleanField(default=True)
    allows = db.StringField()  # db.ListField(db.StringField())
    denies = db.StringField()  # db.ListField(db.StringField())
    process_value = db.StringField()

    def to_conf(self):
        data = {
            'page': self.page.alias,
            'sel_type': self.sel_type,
            'selector': self.selector,
            'df_enable': self.df_enable,
            'allows': list(map(lambda s: s.strip(), self.allows.split('\n'))) if self.allows else None,
            'denies': list(map(lambda s: s.strip(), self.denies.split('\n'))) if self.denies else None,
            'process_value': self.process_value
        }
        return data


DATATYPES = [
    ('', ''),
    ('str', 'String'),
    ('int', 'Integer'),
    ('float', 'Float'),
    ('datetime', 'DateTime')
]


class ItemField(db.EmbeddedDocument):
    # meta = {
    #     'abstract': True,
    # }
    name = db.StringField(required=True, min_length=0, max_length=255)
    required = db.BooleanField(default=False)
    sel_type = db.StringField(required=True, default='css', choices=[('css', 'CSS'), ('xpath', 'XPath')])
    selector = db.StringField(required=True, min_length=1, max_length=500)
    default = db.StringField(required=False, max_length=255)
    data_type = db.StringField(required=False, default='', choices=DATATYPES)
    process_value = db.StringField()

    def to_conf(self):
        data = {
            'name': self.name,
            'required': self.required,
            'sel_type': self.sel_type,
            'selector': self.selector,
            'default': self.default,
            'data_type': self.data_type,
            'process_value': self.process_value
        }
        return data

# class ItemField(Field):
#     children = db.EmbeddedDocumentListField(Field)


# class ItemDocument(db.EmbeddedDocument):
#     type = db.StringField(required=True, choices=['', 'conf', 'code'])
#     fields = db.EmbeddedDocumentListField(ItemField)
#     pycode = db.StringField()
#     datastore = db.ReferenceField('Datastore')


class Page(Document):
    _meta = {
        'indexes': []
    }
    _form_subdocuments = {
        'link_rules': LinkRule,
        'item_fields': ItemField
    }
    name = db.StringField(required=True, min_length=1, max_length=150, unique=True)
    alias = db.StringField(required=True, min_length=1, max_length=150, unique_with='project')
    project = db.ReferenceField('Project', required=True, reverse_delete_rule=2)
    # is_entry = db.BooleanField(default=False)
    status = db.IntField(default=0)
    priority = db.IntField(default=5)
    method = db.StringField(default='GET', choices=['GET', 'POST'])
    before_request = db.StringField()
    after_response = db.StringField()
    encoding = db.StringField(max_length=50)
    headers = db.DictField()
    save_type = db.IntField(default=0, choices=[(0, u'默认'), (1, u'解析失败时'), (2, u'保存')])
    # data = db.DictField()
    query_clean = db.StringField(max_length=200)
    valid_code = db.StringField(max_length=100)
    test_html = db.StringField()
    test_url = db.StringField(max_length=500)
    test_conf = db.DictField()
    js_enable = db.BooleanField(default=False)
    js_code = db.StringField()
    js_timeout = db.IntField(default=30)

    link_type = db.StringField(default='', choices=[('', u'不抽取'), ('conf', u'规则抽取'), ('code', u'Py代码抽取')])
    link_rules = db.ListField(db.EmbeddedDocumentField(LinkRule))
    link_pycode = db.StringField()

    item_type = db.StringField(default='', choices=[('', u'不解析'), ('conf', u'规则解析'), ('code', u'Py代码解析')])
    item_fields = db.ListField(db.EmbeddedDocumentField(ItemField))
    item_pycode = db.StringField()
    save_script = db.ReferenceField('Script', reverse_delete_rule=3)
    # links = db.EmbeddedDocumentField(LinkDocument)
    # items = db.EmbeddedDocumentField(ItemDocument)

    owner = db.ReferenceField('User')
    created = db.DateTimeField(default=datetime.now)
    updated = db.DateTimeField()
    published = db.DateTimeField()

    def __unicode__(self):
        return '%s / %s' % (self.name, self.alias)

    def to_conf(self):
        data = {}
        attrs = ('priority', 'method', 'encoding', 'js_enable', 'link_type',
                 'item_type', 'before_request', 'after_response')
        for attr in attrs:
            data[attr] = getattr(self, attr, None)

        data['headers'] = dict(self.headers)

        if self.valid_code:
            codes = [code.strip() for code in self.valid_code.replace(',', '\n').split('\n')]
            codes = filter(lambda c: c and c.isdigit(), codes)
            data['valid_code'] = [int(c) for c in codes]

        if self.query_clean:
            query_clean = [qc.strip() for qc in self.query_clean.split('\n')]
            data['query_clean'] = filter(lambda c: c, query_clean)

        if self.js_enable:
            data['js_code'] = self.js_code
            data['js_timeout'] = self.js_timeout

        if self.link_type == 'conf':
            rules = []
            for r in self.link_rules:
                rule = r.to_conf()
                rules.append(rule)
            data['link_rules'] = rules
        elif self.link_type == 'code':
            data['link_pycode'] = self.link_pycode

        if self.item_type == 'conf':
            fields = []
            for f in self.item_fields:
                field = f.to_conf()
                fields.append(field)
            data['item_fields'] = fields
        elif self.item_type == 'code':
            data['item_pycode'] = self.item_pycode

        if self.save_script:
            data['save_script'] = self.save_script.alias

        return data


