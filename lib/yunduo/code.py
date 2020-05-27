
import sys
import types
from datetime import datetime, timedelta
import six
from six.moves import builtins as __builtins__
# from connections import redis_conf
# from .functional import str_encode
from celery._state import get_current_task
from yunduo.conf import xconf
from yunduo.utils import merge
from yunduo.errors import FunctionNotFound


MAX_LIVE = timedelta(900)  # 15min

sys.modules['__scripts__'] = __scripts__ = types.ModuleType('__scripts__', 'The __scripts__ module')
__my__builtins__ = {}
if type(__builtins__) is dict:
    __my__builtins__ = __builtins__.copy()
    __import__original = __builtins__['__import__']
else:
    __import__original = __builtins__.__import__
    for name in dir(__builtins__):
        __my__builtins__[name] = getattr(__builtins__, name)


class FakeModule(object):
    pass


def get_function(pycode, name=None, env=None, **kw):
    func = None
    mod = compile(pycode, env, **kw)
    # if func_name is None:
    #     func_name = kwargs.get('func_name', None)
    if name:
        func = mod.get(name)
    if not func and '__entry__' in mod:
        func = mod.get('__entry__', None)
        if isinstance(func, six.string_types):
            func = mod.get(func, None)

    if func is None:
        raise FunctionNotFound('function %s or __entry__ is Not Found.', name)

    return func


# def get_action(name, env, **kw):
#     proj = kw.pop('project', None)
#     act = conf.get_action(proj, name)


def get_script(name, env=None, **kw):
    func = kw.pop('function', None)
    if '.' in name:
        project, _, name = name.rpartition('.')
    else:
        project = kw.pop('project', None)
        if not project and env:
            environ = env.get('environ')
            if environ and 'project' in environ:
                project = environ['project']

    # if proj:
    #     key = '%s:script:%s' % (proj, name)
    # else:
    #     key = 'script:%s' % name
    scr = xconf.get_script(project, name)
    pycode = scr['pycode']
    # g = {}
    # if env:
    #     g.update(env)
    # g.update(kw)
    # g.update({'__builtins__': __my__builtins__.copy()})
    # six.exec_(pycode, g)
    g = compile(pycode, env, **kw)

    mod_name = '%s_%s' % (project if project else '', name)
    mod = types.ModuleType('script_%s' % mod_name, 'The __scripts__.%s Script Module' % (mod_name,))
    for key in g:
        setattr(mod, key, g[key])
    setattr(mod, '__created__', datetime.now())

    if func:
        ffunc = None
        if isinstance(func, six.string_types):
            ffunc = getattr(mod, func, None)
        else:
            if hasattr(mod, '__entry__'):
                ffunc = getattr(mod, '__entry__', None)
                if isinstance(ffunc, six.string_types):
                    ffunc = getattr(mod, ffunc, None)
        return ffunc

    return mod


def __scripts__import__(name, globals_=None, locals_=None, fromlist=None, level=-1):
    '''from __scripts__ import xxx OR from __scripts__.xxx import yyy'''
    attrs, project = None, None
    if name.startswith('__project__'):
        env = globals_.get('environ')
        if env:
            project = env.get('project')

        if not project:
            task = get_current_task()
            if not task:
                raise ImportError('No module named %s (current task is None)' % name)
            b = task.brief()
            project = b.get('project')
            if not project:
                raise ImportError('No module named %s (project is None)' % name)

        attrs = name.split('.', 1)
        attrs.pop(0)
    elif name.startswith('__scripts__'):
        attrs = name.split('.', 1)
        attrs.pop(0)
    else:
        return __import__original(name, globals_, locals_, fromlist, level)

    if attrs:
        for attr in attrs:
            mod_name = '%s_%s' % (project if project else '', attr)
            if hasattr(__scripts__, mod_name):
                submod = getattr(__scripts__, mod_name)
                if submod.__created__ - datetime.now() < MAX_LIVE:
                    return submod

            submod = get_script(attr, globals_, project=project)
            setattr(__scripts__, mod_name, submod)
            return submod

    elif fromlist:
        obj = FakeModule()
        for attr in fromlist:
            mod_name = '%s_%s' % (project if project else '', attr)
            if hasattr(__scripts__, mod_name):
                submod = getattr(__scripts__, mod_name)
                if submod.__created__ - datetime.now() < MAX_LIVE:
                    setattr(obj, attr, submod)
                    continue
            submod = get_script(attr, globals_, project=project)
            setattr(__scripts__, mod_name, submod)
            setattr(obj, attr, submod)
        return obj
    else:
        raise ImportError('No module named %s (__scripts__import__)' % name)


__my__builtins__['__import__'] = __scripts__import__


def compile(code, env=None, **kw):
    # code = str_encode(code)
    g = {}
    if not env:
        env = {}

    g = merge(g, env, kw)

    g['__builtins__'] = __my__builtins__.copy()
    six.exec_(code, g)
    return g
