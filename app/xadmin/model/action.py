# coding=utf8

from datetime import datetime
from .base import db, Document

# InputTypes = [('username', u'用户名'), ('password', u'密码'),
#               ('image', u'图片验证码'), ('sms', u'短信验证码'),
#               ('hidden', u'隐藏字段')]
# InputTypes = [('input', u'文本框'), ('password', u'密码框'), ('image', u'Image'), ('hidden', u'隐藏域'),
#               ('radio', u'单选框')]


# class LoginField(db.EmbeddedDocument):
#     type = db.StringField(required=True, choices=InputTypes)
#     name = db.StringField(required=True, max_length=50)
#     label = db.StringField(required=True, max_length=50)
#     default = db.StringField(max_length=50)
#     props = db.DictField()


# class LoginWay(db.EmbeddedDocument):
#     title = db.StringField(required=True, min_length=2, max_length=50)
#     default = db.BooleanField(default=False)
#     # fields = db.ListField(db.DictField(), required=True)
#     fields = db.ListField(db.EmbeddedDocumentField(LoginField))


# class LoginEvent(db.EmbeddedDocument):
#     name = db.StringField(required=True, min_length=2, max_length=50)
#     expire = db.IntField(default=300)
#     type = db.IntField(default=1, choices=[(0, u'Javscript'), (1, u'Python')])
#     jscode = db.StringField()
#     pycode = db.StringField()


class Action(Document):
    meta = {
        'indexes': ['name', 'alias', 'project']
    }
    name = db.StringField(required=True, min_length=2, max_length=150)
    alias = db.StringField(required=True, min_length=2, max_length=50, unique_with='project')
    project = db.ReferenceField('Project', required=True, reverse_delete_rule=2)
    status = db.IntField(default=0)
    multistage = db.BooleanField(default=False)
    lang = db.IntField(default=1, choices=[(0, u'Javscript'), (1, u'Python')])
    jscode = db.StringField()
    pycode = db.StringField()

    timeout = db.IntField(default=120)

    owner = db.ReferenceField('User')
    created = db.DateTimeField(default=datetime.now())
    updated = db.DateTimeField()
    published = db.DateTimeField()

    def __unicode__(self):
        return "%s / %s" % (self.name, self.alias)

    __str__ = __unicode__

    def to_conf(self):
        data = {
            'lang': self.lang,
            'multistage': self.multistage,
            'jscode': self.jscode if self.lang == 0 else '',
            'pycode': self.pycode if self.lang == 1 else '',
            'timeout': self.timeout,
        }

        return data
