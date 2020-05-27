# coding=utf8

import os
import functools
import redis
import pymysql
import six
from pymysql import cursors
from pymongo import MongoClient
from influxdb import InfluxDBClient
from six.moves.urllib.parse import urlparse, parse_qsl
from celery.local import Proxy
from cachetools import TTLCache
from yunduo.conf import xconf
from yunduo.errors import ConfigError


__cached__ = TTLCache(20, 3600)


def get_redis(url):
    global __cached__
    if '://' not in url:
        cnf = xconf.get_connection(url)
        dsn = cnf.pop('dsn', None) if cnf else None
        if not dsn:
            raise ConfigError(u'连接 %s 设置错误 %s' % (url, cnf))
    else:
        dsn = url

    key = 'redis_%s_%s' % (dsn, os.getpid())
    if key not in __cached__:
        __cached__.update({key: redis.from_url(dsn)})

    return __cached__[key]


def get_mongodb(url, **kw):
    global __cached__
    if '://' not in url:
        cnf = xconf.get_connection(url)
        dsn = cnf.pop('dsn', None) if cnf else None
        if not dsn:
            raise ConfigError(u'连接 %s 设置错误 %s' % (url, cnf))
        kw.update(cnf)
    else:
        dsn = url
    key = 'mongo_%s_%s' % (dsn, os.getpid())
    if key not in __cached__:
        __cached__[key] = MongoClient(dsn)

    conn = __cached__[key]
    db = kw.get('db', 'tmp')

    return conn[db]


def get_mysql(url, **kw):
    global __cached__
    if '://' not in url:
        cnf = xconf.get_connection(url)
        dsn = cnf.pop('dsn', None) if cnf else None
        if not dsn:
            raise ConfigError(u'连接 %s 设置错误 %s' % (url, cnf))
        kw.update(cnf)
    else:
        dsn = url
    key = 'mysql_%s_%s' % (dsn, os.getpid())
    if key not in __cached__:
        pd = urlparse(dsn)
        kwargs = {
            'host': pd.hostname,
            'port': pd.port or 3306
        }
        if pd.username:
            kwargs['user'] = pd.username
            if pd.password:
                kwargs['password'] = pd.password
        if pd.path:
            kwargs['db'] = pd.path[1:]

        if pd.query:
            kwargs.update(dict(parse_qsl(pd.query)))

        kwargs.update(kw)
        cursorclass = kwargs.pop('cursorclass', None)
        if cursorclass:
            if isinstance(cursorclass, six.string_type):
                cc = getattr(cursors, cursorclass, None)
                if cc:
                    kwargs['cursorclass'] = cc
            else:
                kwargs['cursorclass'] = cursorclass

        __cached__[key] = pymysql.connect(**kwargs)

    return __cached__[key]


def get_influxdb(url):
    global __cached__
    if '://' not in url:
        cnf = xconf.get_connection(url)
        dsn = cnf.pop('dsn', None) if cnf else None
        if not dsn:
            raise ConfigError(u'连接 %s 设置错误 %s' % (url, cnf))
    else:
        dsn = url
    return InfluxDBClient.from_dsn(dsn, timeout=5)


def get_connection(name, **kw):
    cnf = xconf.get_connection(name)
    # print(cnf)
    if cnf:
        cnf = cnf.copy()
    else:
        cnf = {}
    dsn = cnf.pop('dsn', None) if cnf else None
    if not dsn:
        raise ConfigError(u'不存在的连接 %s 设置' % name)

    pd = urlparse(dsn)
    scheme = pd.scheme
    if scheme == 'redis':
        return Proxy(functools.partial(get_redis, dsn))
    elif scheme == 'mongodb':
        return Proxy(functools.partial(get_mongodb, dsn, **cnf))
    elif scheme == 'mysql':
        return Proxy(functools.partial(get_mysql, dsn, **cnf))
    elif scheme == 'influxdb':
        return Proxy(functools.partial(get_influxdb, dsn))
    else:
        cnf['dsn'] = dsn
        raise ConfigError(u'连接 %s 设置错误 %s' % (name, cnf))

