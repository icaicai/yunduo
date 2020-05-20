# coding=utf8

from datetime import datetime
from .base import db, Document


class Script(Document):
    meta = {
        'indexes': ['name']
    }
    name = db.StringField(required=True, min_length=2, max_length=150, unique=True)
    alias = db.StringField(required=True, min_length=2, max_length=50, unique_with='project')
    project = db.ReferenceField('Project', required=False, reverse_delete_rule=2)
    status = db.IntField(default=0)
    # type = db.IntField(default=0, choices=[(0, u'通用'), (1, u'存储'), (2, u'告警')])
    tags = db.StringField(max_length=250)
    pycode = db.StringField(required=True)
    owner = db.ReferenceField('User')
    created = db.DateTimeField(default=datetime.now())
    updated = db.DateTimeField()
    published = db.DateTimeField()

    def __unicode__(self):
        return "%s / %s" % (self.name, self.alias)

    def to_conf(self):
        data = {}
        data['tags'] = list(map(lambda t: t.strip(), self.tags.split(','))) if self.tags else []
        data['pycode'] = self.pycode
        return data

# class ScriptSchema(ModelSchema):
#     class Meta:
#         model = Script
#         model_fields_kwargs = {
#             'status': {'dump_only': True},
#             'created': {'dump_only': True},
#             'updated': {'dump_only': True},
#             'published': {'dump_only': True},
#         }

#     modified = fields.Method('is_modified', dump_only=True)

#     def is_modified(self, obj):
#         if obj.status == 1:
#             return obj.published and obj.updated and obj.updated > obj.published
#         return False
