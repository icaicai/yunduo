# coding=utf8

import datetime
from .base import db, Document


# class Rule(db.EmbeddedDocument):
#     field = db.StringField(max_length=20)
#     window = db.IntField()
#     transform = db.StringField(max_length=50)
#     compare = db.StringField(max_length=10)
#     value = db.StringField(max_length=50)
#
#
# class Alert(Document):
#     _meta = {
#         'indexes': ['project', 'job']
#     }
#
#     name = db.StringField(required=True, min_length=1, max_length=50, unique=True)
#     project = db.ReferenceField('Project')
#     job = db.ReferenceField('Job')
#     rules = db.ListField(db.EmbeddedDocumentField(Rule))
#
#     trigger_job = db.StringField(choices=[('', ''), ('pause', '暂停'), ('stop', '停止')])
#     trigger_script = db.ReferenceField('Script')
#     trigger_script_args = db.DictField()
#
#     owner = db.ReferenceField('User')
#     created = db.DateTimeField(default=datetime.datetime.now())
#     updated = db.DateTimeField()

class Alert(Document):
    _meta = {
        'indexes': ['project', 'job']
    }

    name = db.StringField(required=True, min_length=1, max_length=50, unique=True)
    project = db.ReferenceField('Project')
    job = db.ReferenceField('Job')

    event = db.StringField(max_length=50)
    time_range = db.IntField()
    transform = db.StringField(max_length=50)  # mean, sum, alway, once
    compare = db.StringField(max_length=10)  # gt, eq, lt
    value = db.StringField(max_length=50)

    script_1 = db.StringField(max_length=100)
    script_2 = db.StringField(max_length=100)

    status = db.IntField(default=0)
    owner = db.ReferenceField('User')
    created = db.DateTimeField(default=datetime.datetime.now())
    updated = db.DateTimeField()

