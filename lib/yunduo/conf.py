# coding=utf8

import copy
import json
import redis
from cachetools import TTLCache, cached, cachedmethod
from celery.utils.imports import (NotAPackage, find_module, import_from_cwd,
                                  symbol_by_name)
from yunduo.utils import arg_to_iter, merge
# from yunduo.resource import proxy
from yunduo.errors import ConfigError
# from celery.utils.collections import DictAttribute, force_mapping


'''
job
page
blocked
script
action
monitor
'''


class RedisConfig(object):

    __cached_page = TTLCache(128, 1)
    __cached_conf = TTLCache(128, 3)

    def __init__(self):
        self.__conf = {
            'connection': {}
        }

    def from_object(self, path, name='conf'):
        obj = self._load_object(path)
        for k in dir(obj):
            if k.startswith('_'):
                continue
            self.__conf[k] = getattr(obj, k)

        if name not in self.__conf['connection']:
            raise ConfigError(u'请设定配置缓存链接: < redis://...>')

        cc = self.__conf['connection'][name]
        self._redis = redis.from_url(cc['dsn'])

    def _load_object(self, path):
        # imp = import_from_cwd
        if ':' in path:
            # Path includes attribute so can just jump
            # here (e.g., ``os.path:abspath``).
            return symbol_by_name(path, imp=import_from_cwd)

        # Not sure if path is just a module name or if it includes an
        # attribute name (e.g., ``os.path``, vs, ``os.path.abspath``).
        try:
            return import_from_cwd(path)
        except ImportError:
            # Not a module name, so try module + attribute.
            return symbol_by_name(path, imp=import_from_cwd)

    # def setup(self, dsn, **kw):
    #     self._redis = redis.from_url(dsn)
    #     # maxsize = kw.pop('maxsize', 128)
    #     # ttltime = kw.pop('ttl', 600)
    #     # self.cached = TTLCache(maxsize, ttltime)
    #     self.__conf.setdefault('connection', {})
    #     self.__conf.update(kw)

    def clear(self):
        self.__cached_page.clear()
        self.__cached_conf.clear()

    def serialize(self, data):
        pass

    def unserialize(self, data):
        return json.loads(data)

    def raw_set(self, name, key, value=None):
        if isinstance(key, dict):
            self._redis.hmset(name, key)
        else:
            self._redis.hset(name, key, value)

    def raw_get(self, name, key=None, *keys):
        field = arg_to_iter(key)
        field.extend(keys)

        if field:
            value = self._redis.hmget(name, field)
            if len(field) == 1:
                return value[0]
            return dict(zip(field, value))
        else:
            data = self._redis.hgetall(name)
            for k in data:
                data[k] = json.loads(data[k])
            return data

    def _get(self, name, key=None, *keys):
        field = arg_to_iter(key)
        field.extend(keys)
        try:
            if name.startswith('conf:'):
                _conf = self.__conf.get(name[5:])
                if _conf:
                    if field:
                        if len(field) == 1:
                            return copy.deepcopy(_conf.get(field[0]))
                        return dict([(k, copy.deepcopy(_conf.get(k))) for k in field])
                    else:
                        return copy.deepcopy(_conf)

            if field:
                value = self._redis.hmget(name, field)
                value = [None if v is None else json.loads(v) for v in value]
                if len(value) == 1:
                    return value[0]
                return dict(zip(field, value))
            else:
                # if name in self.__conf:
                #     return self.__conf[name]

                data = self._redis.hgetall(name)
                for k in data:
                    data[k] = json.loads(data[k])
                return data
        except Exception as e:
            raise ConfigError(u'获取设置错误 %s [ %s ]\n%s' % (name, ', '.join(field), e))

    def _set(self, name, key, value=None):
        if isinstance(key, dict):
            data = dict([(k, json.dumps(v)) for k, v in key.items()])
            self._redis.hmset(name, data)
        else:
            self._redis.hset(name, key, json.dumps(value))

    def _delete(self, name, key=None):
        if key:
            self._redis.hdel(name, key)
        else:
            self._redis.delete(name)

    @cached(__cached_conf)
    def get(self, key, default=None):
        val = self._get('conf:common', key)
        if val is None:
            return default
        return val

    def set(self, key, value=None):
        return self._set('conf:common', key, value)

    @cached(__cached_conf)
    def get_connection(self, key):
        conn = self.__conf['connection']
        if key in conn:
            return conn[key]

        conf = self._get('conf:connection', key)
        if conf:
            return conf[key]
        return None

    def set_connection(self, key, value=None):
        return self._set('conf:connection', key, value)

    @cached(__cached_conf)
    def get_http(self, key=None, *keys):
        return self._get('conf:http', key, *keys)

    @cached(__cached_conf)
    def get_proxy(self, key=None, *keys):
        return self._get('conf:proxy', key, *keys)

    @cached(__cached_page)
    def get_page(self, project, job, page):
        name = 'project:%s' % project
        key_job = 'job:%s' % job
        key_page = 'page:%s' % page
        conf = self._get(name, key_job, key_page)
        c = {}
        c = merge(c, conf[key_job], conf[key_page])
        return c

    def set_page(self, project, page, data):
        name = 'project:%s' % project
        key = 'page:%s' % page
        return self._set(name, key, data)

    def del_page(self, project, page):
        name = 'project:%s' % project
        key = 'page:%s' % page
        return self._delete(name, key)

    @cached(__cached_page)
    def get_form(self, project, form=None, tag=None):
        name = 'project:%s' % project
        if form is None:
            ways = []
            for _, way in self._redis.hscan_iter(name, 'form:*'):
                frm = json.loads(way)
                if not tag or frm['tags'] == tag:
                    ways.append(frm)
            return ways

        key = 'form:%s' % form
        return self._get(name, key)

    def set_form(self, project, form, data):
        name = 'project:%s' % project
        key = 'form:%s' % form
        return self._set(name, key, data)

    def del_form(self, project, form):
        name = 'project:%s' % project
        key = 'form:%s' % form
        return self._delete(name, key)

    @cached(__cached_page)
    def get_job(self, project, job):
        name = 'project:%s' % project
        key = 'job:%s' % job
        return self._get(name, key)

    def set_job(self, project, job, data):
        name = 'project:%s' % project
        key = 'job:%s' % job
        return self._set(name, key, data)

    def del_job(self, project, job):
        name = 'project:%s' % project
        key = 'job:%s' % job
        return self._delete(name, key)

    @cached(__cached_page)
    def get_action(self, project, action):
        if project is None:
            name = 'global:action'
        else:
            name = 'project:%s' % project
        key = 'action:%s' % action
        return self._get(name, key)

    def set_action(self, project, action, data):
        if project is None:
            name = 'global:action'
        else:
            name = 'project:%s' % project
        key = 'action:%s' % action
        return self._set(name, key, data)

    def del_action(self, project, action):
        if project is None:
            name = 'global:action'
        else:
            name = 'project:%s' % project
        key = 'action:%s' % action
        return self._delete(name, key)

    @cached(__cached_page)
    def get_script(self, project, script):
        if project is None:
            name = 'global:script'
        else:
            name = 'project:%s' % project
        key = 'script:%s' % script
        return self._get(name, key)

    def set_script(self, project, script, data):
        if project is None:
            name = 'global:script'
        else:
            name = 'project:%s' % project
        key = 'script:%s' % script
        return self._set(name, key, data)

    def del_script(self, project, script):
        if project is None:
            name = 'global:script'
        else:
            name = 'project:%s' % project
        key = 'script:%s' % script
        return self._delete(name, key)
        # authorization

    @cached(__cached_page)
    def get_blocked(self, project, job):
        name = 'project:%s' % project
        key = 'blocked:%s' % job
        return self._get(name, key)

    def set_blocked(self, project, job, data):
        name = 'project:%s' % project
        key = 'blocked:%s' % job
        return self._set(name, key, data)

    def del_blocked(self, project, job):
        name = 'project:%s' % project
        key = 'blocked:%s' % job
        return self._delete(name, key)


xconf = RedisConfig()

