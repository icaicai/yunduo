# coding=utf8

import datetime
from .base import db, Document


class Project(Document):
    _meta = {
        'indexes': ['name', 'alias']
    }
    name = db.StringField(required=True, min_length=1, max_length=150, unique=True)
    alias = db.StringField(required=True, min_length=1, max_length=50, unique=True)
    # type = db.IntField(default=0, choices=[(0, u'普通'), (1, u'授权')])
    status = db.IntField(default=0)
    # entry_url = db.URLField(required=True, min_legth=4)
    # entry_page = db.ReferenceField('Page')
    # entry_page = db.StringField(min_legth=1, max_length=50)
    # tags = db.ListField(db.StringField(max_length=150))
    # periodic = db.StringField(max_length=50)
    # priority = db.IntField(default=-1)
    # rate_limit = db.StringField(max_length=50)
    # max_retries = db.IntField(default=-1)
    # use_proxy = db.BooleanField(default=False)  #
    # df_expire = db.StringField(max_length=50)   #
    # headers = db.StringField()
    # page_save = db.IntField(default=0, choices=[(0, u'不保存'), (1, u'解析失败时'), (2, u'所有页面')])
    # cookie_type = db.IntField(default=0, choices=[(0, u'不使用'), (1, u'即时'), (2, u'持久')])
    # finish_script = db.StringField(max_length=150)

    # blocked_code = db.StringField()
    # blocked_text = db.StringField()
    # blocked_retry = db.IntField(default=0)

    # fetch_mon_rate_1 = db.StringField(max_length=50)
    # fetch_mon_rate_2 = db.StringField(max_length=50)
    # fetch_mon_script_1 = db.StringField(max_length=150)
    # fetch_mon_script_2 = db.StringField(max_length=150)
    # parse_mon_rate_1 = db.StringField(max_length=50)
    # parse_mon_rate_2 = db.StringField(max_length=50)
    # parse_mon_script_1 = db.StringField(max_length=150)
    # parse_mon_script_2 = db.StringField(max_length=150)
    # fetch_fail_action = db.ListField(db.StringField(max_length=50))
    # max_parse_fail = db.StringField(max_length=50)
    # parse_fail_action = db.ListField(db.StringField(max_length=50))
    owner = db.ReferenceField('User')
    created = db.DateTimeField(default=datetime.datetime.now())
    updated = db.DateTimeField()
    published = db.DateTimeField()

    def __unicode__(self):
        return "%s / %s" % (self.name, self.alias)
