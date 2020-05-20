# coding=utf8

import datetime
from .base import db, Document


class Blocked(Document):
    _meta = {
        'indexes': ['name', 'project']
    }
    name = db.StringField(required=True, min_length=1, max_length=50, unique=True)
    alias = db.StringField(required=True, min_length=1, max_length=150, unique_with='project')

    project = db.ReferenceField('Project')

    type = db.StringField(required=True, choices=[('code', u'Code'), ('text', u'Text'), ('script', 'Script')])
    status = db.IntField(required=True, default=0)
    text = db.StringField()
    # pycode = db.StringField()
    # entry_url = db.URLField(required=True, min_legth=4)
    # entry_page = db.StringField(min_legth=1, max_length=50)
    # action = db.ReferenceField('Action')
    # tags = db.ListField(db.StringField(max_length=150))

    # blocked_code = db.StringField()
    # blocked_text = db.StringField()
    # blocked_retry = db.IntField(default=0)

    trigger_project = db.StringField(choices=[('', ''), ('pause', '暂停'), ('stop', '停止')])
    trigger_script = db.ReferenceField('Script')
    trigger_script_args = db.DictField()

    owner = db.ReferenceField('User')
    created = db.DateTimeField(default=datetime.datetime.now())
    updated = db.DateTimeField()
    published = db.DateTimeField()

    def __unicode__(self):
        return "%s / %s" % (self.name, self.alias)

    def to_conf(self):

        data = {

        }

        return data
