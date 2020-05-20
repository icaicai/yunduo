# coding=utf8

from datetime import datetime
from .base import db, Document

# InputTypes = [('username', u'用户名'), ('password', u'密码'),
#               ('image', u'图片验证码'), ('sms', u'短信验证码'),
#               ('hidden', u'隐藏字段')]
InputTypes = [('input', u'文本框'), ('password', u'密码框'), ('image', u'图像'), ('hidden', u'隐藏域'),
              ('radio', u'单选框')]


class LoginField(db.EmbeddedDocument):
    type = db.StringField(required=True, choices=InputTypes)
    name = db.StringField(required=True, max_length=50)
    label = db.StringField(required=True, max_length=50)
    default = db.StringField(max_length=50)
    action = db.ReferenceField('Action', required=False)
    trigger = db.BooleanField(default=False)
    props = db.DictField()

    def to_conf(self):
        data = {
            'type': self.type,
            'name': self.name,
            'label': self.label,
            'default': self.default,
            'props': self.props.to_python(),
            'action': self.action.alias if self.action else '',
            'trigger': self.trigger
        }
        return data


class LoginWay(db.EmbeddedDocument):
    title = db.StringField(required=True, min_length=2, max_length=50)
    default = db.BooleanField(default=False)
    # fields = db.ListField(db.DictField(), required=True)
    fields = db.ListField(db.EmbeddedDocumentField(LoginField))
    action = db.ReferenceField('Action', required=True)
    created = db.DateTimeField(default=datetime.now())

    def to_conf(self):
        fields = []
        data = {
            'default': self.default,
            'title': self.title,
            'action': self.action.alias if self.action else '',
            'fields': fields
        }
        for field in self.fields:
            fields.append(field.to_conf())
        return data


class Accredit(Document):
    meta = {
        'indexes': ['name', 'project']
    }
    name = db.StringField(required=True, min_length=2, max_length=150, unique=True)
    # alias = db.StringField(required=True, min_length=2, max_length=50, unique=True)
    # category = db.StringField(required=True, choices=[('ds', u'电商'), ('sb', u'社保'), ('yys', u'运营商')])
    project = db.ReferenceField('Project', required=True, reverse_delete_rule=2)
    status = db.IntField(default=0)

    ways = db.ListField(db.EmbeddedDocumentField(LoginWay))

    owner = db.ReferenceField('User')
    created = db.DateTimeField(default=datetime.now())
    updated = db.DateTimeField()
    published = db.DateTimeField()

    def __unicode__(self):
        return "%s / %s" % (self.name, self.alias)

    def to_conf(self):
        ways = []
        data = {
            'name': self.name,
            'ways': ways,
        }
        for way in self.ways:
            ways.append(way.to_conf())

        return data
