# coding=utf8

from datetime import datetime
from .base import db, Document

# InputTypes = [('username', u'用户名'), ('password', u'密码'),
#               ('image', u'图片验证码'), ('sms', u'短信验证码'),
#               ('hidden', u'隐藏字段')]
InputTypes = [('input', u'文本框'), ('password', u'密码框'), ('image', u'图像'), ('imginp', u'图像带输入框'),
              ('hidden', u'隐藏域'), ('radio', u'单选框')]


class Field(db.EmbeddedDocument):
    type = db.StringField(required=True, choices=InputTypes)
    name = db.StringField(required=True, max_length=50)
    label = db.StringField(required=True, max_length=50)
    default = db.StringField(max_length=50)
    action = db.ReferenceField('Action', required=False)
    trigger = db.BooleanField(default=False)
    props = db.DictField()

    def to_conf(self):
        # print(self.props, dir(self.props), type(self.props))
        data = {
            'type': self.type,
            'name': self.name,
            'label': self.label,
            'default': self.default,
            'props': self.props,
            'action': self.action.alias if self.action else '',
            'action_name': self.action.name if self.action else '',
            'trigger': self.trigger
        }
        return data


class Form(Document):
    meta = {
        'indexes': []
    }
    name = db.StringField(required=True, min_length=2, max_length=50, unique=True)
    alias = db.StringField(required=True, min_length=2, max_length=50, unique_with='project')
    project = db.ReferenceField('Project', required=True, reverse_delete_rule=2)
    status = db.IntField(default=0)
    tags = db.StringField(default='login', choices=[('login', '登录'), ('other', '其他')], max_length=20)
    # default = db.BooleanField(default=False)
    sequence = db.IntField(default=0)
    # fields = db.ListField(db.DictField(), required=True)
    fields = db.ListField(db.EmbeddedDocumentField(Field))
    action = db.ReferenceField('Action', required=False, reverse_delete_rule=2)
    job = db.ReferenceField('Job', required=False, reverse_delete_rule=2)

    owner = db.ReferenceField('User')
    created = db.DateTimeField(default=datetime.now())
    updated = db.DateTimeField()
    published = db.DateTimeField()

    def __unicode__(self):
        return "%s / %s" % (self.name, self.alias)

    def to_conf(self):
        fields = []
        data = {
            # 'default': self.default,
            'name': self.name,
            'alias': self.alias,
            'sequence': self.sequence,
            'tags': self.tags,
            'action': self.action.alias if self.action else '',
            'job': self.job.alias if self.job else '',
            'fields': fields
        }
        for field in self.fields:
            fields.append(field.to_conf())
        return data


# class Accredit(Document):
#     meta = {
#         'indexes': ['name', 'project']
#     }
#     name = db.StringField(required=True, min_length=2, max_length=150, unique=True)
#     # alias = db.StringField(required=True, min_length=2, max_length=50, unique=True)
#     # category = db.StringField(required=True, choices=[('ds', u'电商'), ('sb', u'社保'), ('yys', u'运营商')])
#     project = db.ReferenceField('Project', required=True, reverse_delete_rule=2)
#     status = db.IntField(default=0)
#
#     ways = db.ListField(db.EmbeddedDocumentField(LoginWay))
#
#     owner = db.ReferenceField('User')
#     created = db.DateTimeField(default=datetime.now())
#     updated = db.DateTimeField()
#     published = db.DateTimeField()
#
#     def __unicode__(self):
#         return "%s / %s" % (self.name, self.alias)
#
#     def to_conf(self):
#         ways = []
#         data = {
#             'name': self.name,
#             'ways': ways,
#         }
#         for way in self.ways:
#             ways.append(way.to_conf())
#
#         return data
