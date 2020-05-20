# coding=utf8

import time
import datetime
import uuid
from mongoengine import signals
from yunduo.utils import base_convert, gen_id
from yunduo.rate import parse_rate
from .base import db, Document


def gen_batch_id(prefix):
    u = uuid.uuid4()
    t = base_convert(int(time.time()))
    r = base_convert(u.time)
    return '%s%s%s' % (prefix.rjust(3, 'x'), t.rjust(6, '0')[:6], r.rjust(6, '0')[:6])  # 2038


class Job(Document):
    _meta = {
        'indexes': []
    }
    name = db.StringField(required=True, min_length=1, max_length=150)
    alias = db.StringField(required=True, min_length=1, max_length=50, unique_with='project')
    type = db.IntField(default=0, choices=[(0, u'普通'), (1, u'调度'), (2, u'授权')])
    status = db.IntField(default=0)
    tags = db.ListField(db.StringField(max_length=50))
    project = db.ReferenceField('Project')
    entry_url = db.URLField(min_legth=4, max_length=500)
    # entry_page = db.StringField(min_legth=1, max_length=50)
    entry_type = db.IntField(default=0, choices=[(0, u'页面'), (1, u'脚本')])
    entry_page = db.ReferenceField('Page')
    entry_script = db.ReferenceField('Script')

    entry_script_args = db.StringField()
    last_batch_id = db.StringField(max_length=32)

    schedule = db.StringField(max_length=50)
    schedule_type = db.StringField(max_length=10,
                                   choices=[('datetime', u'定时'), ('schedule', u'定期'), ('crontab', 'Crontab')])
    priority = db.IntField(default=5, choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9)])
    rate_limit = db.StringField(max_length=50)
    max_retries = db.IntField(default=-1)
    incr_mode = db.BooleanField(default=False)

    http_valid_code = db.StringField(default='', max_length=500)
    http_retry_code = db.StringField(default='', max_length=500)
    proxy_type = db.StringField(default='__f__', max_length=32, choices=[('__f__', u'不使用'), ('__t__', u'随机'), ('__g__', u'指定组')])  #
    cookie_type = db.StringField(default='__f__', max_length=32, choices=[('__f__', u'不使用'), ('__t__', u'跟随'), ('__g__', u'指定组')])
    df_expire = db.IntField(default=-1)   #
    df_query_only = db.StringField()
    df_query_remove = db.StringField()
    save_page = db.IntField(default=0, choices=[(0, u'不保存'), (1, u'解析失败时'), (2, u'保存')])
    headers = db.DictField()

    deny_code = db.StringField(default='')
    deny_text = db.StringField(default='')
    deny_script = db.StringField(default='')
    deny_retry = db.BooleanField(default=True)
    deny_delay = db.IntField(default=60)

    finish_script = db.StringField(max_length=150)

    # last_run = db.DateTimeField()

    # last_batch = db.ReferenceField('JobBatch')

    owner = db.ReferenceField('User')
    created = db.DateTimeField(default=datetime.datetime.now())
    updated = db.DateTimeField()

    def __init__(self, *args, **kwargs):
        super(Job, self).__init__(*args, **kwargs)
        self._last_batch_obj = None

    def __unicode__(self):
        return "%s / %s" % (self.name, self.alias)

    def save(self):
        if self._last_batch_obj:
            self._last_batch_obj.save()
            self.last_batch_id = self._last_batch_obj.batch_id
        return super(Job, self).save()

    @property
    def last_batch(self):
        if self._last_batch_obj:
            return self._last_batch_obj
        # self._last_batch_obj = JobBatch.objects(job=self).order_by('-created').first()
        if self.last_batch_id:
            self._last_batch_obj = JobBatch.objects(batch_id=self.last_batch_id).first()
        return self._last_batch_obj

    def new_batch(self):
        self._last_batch_obj = JobBatch()
        # self.last_batch_id = self._last_batch_obj.id
        self._last_batch_obj.job = self

        return self._last_batch_obj

    def to_conf(self):
        _type = {'__f__': False, '__t__': True}
        data = {}
        attrs = ('name', 'alias', 'entry_type', 'priority', 'incr_mode',
                 'save_page', 'headers')
        for attr in attrs:
            value = getattr(self, attr)
            if value is not None:
                data[attr] = value

        if self.entry_type == 0:
            data['entry_url'] = self.entry_url
            data['entry_page'] = self.entry_page.alias
        elif self.entry_type == 1:
            data['entry_script'] = self.entry_script.alias

        if self.max_retries > 0:
            data['max_retries'] = self.max_retries
        if self.df_expire > 0:
            data['df_expire'] = self.df_expire
        if self.df_query_only:
            data['df_query_only'] = list(map(lambda s: s.strip(), self.df_query_only.split('\n')))
        if self.df_query_remove:
            data['df_query_remove'] = list(map(lambda s: s.strip(), self.df_query_remove.split('\n')))

        data['rate_limit'] = self.rate_limit
        data['proxy_type'] = _type.get(self.proxy_type, self.proxy_type)
        data['cookie_type'] = _type.get(self.cookie_type, self.cookie_type)

        if self.http_retry_code:
            data['http_retry_code'] = list(map(int, self.http_retry_code.replace(',', '\n').split('\n')))
        if self.deny_code:
            data['deny_code'] = list(map(int, self.deny_code.replace(',', '\n').split('\n')))
        if self.deny_text:
            data['deny_text'] = list(map(lambda s: s.strip(), self.deny_text.split('\n')))
        if self.deny_script:
            data['deny_script'] = self.deny_script

        return data


class JobBatch(Document):
    batch_id = db.StringField(required=True, max_length=20, unique=True)
    job = db.ReferenceField(Job, required=True, reverse_delete_rule=2)
    created = db.DateTimeField(default=datetime.datetime.now())
    finished = db.DateTimeField()
    stopped = db.DateTimeField()

    def is_finished(self):
        return self.stopped or (self.finished and self.finished > self.created)

    def finish(self):
        self.finished = datetime.datetime.now()
        self.save()

    def stop(self):
        self.stopped = datetime.datetime.now()
        self.save()

    def __str__(self):
        return "%s / %s" % (self.job.name, self.batch_id)


def job_batch_post_init(sender, document, **kwargs):
    if not document.batch_id:
        document.batch_id = gen_id('job')


signals.post_init.connect(job_batch_post_init, sender=JobBatch)

