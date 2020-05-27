# coding=utf8

import six
from w3lib.url import canonicalize_url, url_query_cleaner
from celery.utils.encoding import str_to_bytes
from yunduo.conf import xconf
from yunduo.utils import arg_to_iter, md5sum
# from connections import redis_df
from yunduo.resource import get_connection


class Dupefilter(object):

    def __init__(self):
        self.expire = xconf.get('df_expire', 1296000)
        self.redisobj = get_connection('df')

    def seen(self, project, job, lnk, **kw):
        # print 'dupefilter.filter %s' % kw
        # tmp = kw.pop('tmp', False)
        if kw.get('batch_id') and not kw.get('incr_mode'):
            ex = ':%s' % kw['batch_id']
        else:
            ex = ''

        if lnk.df_enable:
            key = 'dupe|%s:%s%s' % (project, job, ex)
        else:
            key = 'dupe:tmp|%s:%s%s' % (project, job, ex)

        expire = kw.pop('expire', self.expire)
        lkey = self.fingerprint(lnk, **kw)
        rlt = self.redisobj.sadd(key, lkey)
        self.redisobj.expire(key, expire)
        return rlt == 0

    def fingerprint(self, lnk, **kw):
        url = canonicalize_url(lnk.url)
        # pconf = kw.get('conf')
        # if not pconf:
        #     pconf = xconf.get_page(project, job, lnk.page)
        qo = kw.get('df_query_only')
        qr = kw.get('df_query_remove')
        if qo:
            url = url_query_cleaner(url, arg_to_iter(qo), remove=False)
        if qr:
            url = url_query_cleaner(url, arg_to_iter(qr), remove=True)

        cnf = lnk.conf
        mds = [lnk.page, url]
        for key in ('method', 'headers', 'data', 'params', 'auth', 'cookies'):
            mds.append(cnf.get(key))

        return md5sum(mds)

        # if not kw:
        #     return md5sum(url)

        # s1 = []
        # for key in kw:
        #     s1.append('%s:%s' % (key, self._hash(kw[key])))

        # return '%s:%s' % (md5sum(url), md5sum('|'.join(s1)))

    # def _hash(self, obj):
    #     s1 = ''
    #     try:
    #         if isinstance(obj, six.string_types):
    #             s1 = ':%s' % md5sum(str_to_bytes(obj))
    #         elif isinstance(obj, dict):
    #             s = sorted(obj.items(), key=lambda t: t[0])
    #             s1 = ':%s' % md5sum(repr(s))
    #         else:
    #             s = sorted(obj, key=lambda t: t[0])
    #             s1 = ':%s' % md5sum(repr(s))
    #     except Exception:
    #         s1 = ':%s' % md5sum(repr(obj))
    #     return s1

    def delete(self, project, job, batch_id=None, **kw):
        if batch_id and not kw.get('incr_mode'):
            ex = ':%s' % batch_id
        else:
            ex = ''

        key = 'dupe|%s:%s%s' % (project, job, ex)
        self.redisobj.delete(key)
        if kw.get('tmp', True):
            key = 'dupe:tmp|%s:%s%s' % (project, job, ex)
            self.redisobj.delete(key)


