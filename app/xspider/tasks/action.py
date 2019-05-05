# coding=utf8

import six
import base64
import json
from datetime import datetime
# from cookielib import CookieJar
from six.moves.http_cookiejar import CookieJar

from requests.utils import dict_from_cookiejar
from kombu.entity import Exchange, Queue
from celery.utils.saferepr import saferepr
from yunduo.conf import xconf
from yunduo.downloader.models import Response
from yunduo.code import get_script, get_function, compile
from yunduo.resource import get_connection
from yunduo.downloader import download, Phantomjs, Request
from yunduo.downloader.phantomjs import PhantomjsTimeout
from xspider.app import app
# from xspider.jobaction import gen_queue_name
from .base import StrategyTask

'''
Result Struct
{
    __notify__: true         # js 用
    status: OK/NXA/NXF/ERR
    data: {}
    cookies: {}
    action: next_action_name
    form: next_form_name
    task: {
        project:
        action:
        batch_id:
    }
    source:
    message:
}
'''

class ProxyLogger(object):

    def __init__(self, logger):
        for meth in ('info', 'warning', 'exception', 'error'):
            setattr(self, meth, lambda msg, *a, **kw: getattr(logger, meth)('PyCode: %s' % msg, *a, **kw))


class DuplexPhantomjs(Phantomjs):

    def __init__(self, send_notify):
        super(DuplexPhantomjs, self).__init__()
        self.send_notify = send_notify

    def process(self, data):
        # d = data.copy()
        # c = d.pop('content', None)
        # print 'DuplexPhantomjs process data %s %s' % (d, c[:10] if c else c)
        if data.get('__notify__'):
            # data = data['data']
            self.send_notify(data)


class ActionTask(StrategyTask):
    # Strategy = 'xspider.strategy:default'

    def initialize(self):
        super(ActionTask, self).initialize()
        self.exchange = Exchange('xaction', type='direct')
        self._inner_logger = ProxyLogger(self.logger)

    def brief(self, args=None, kwargs=None):
        req = self.request
        if not req and not args:
            return {}

        args = args or req.args
        kwargs = kwargs or (req and req.kwargs) or {}

        info = {
            'project': args[0],
            'action': args[1],
            'batch_id': kwargs.get('batch_id'),
        }

        return info

    def report_stat(self, project, action, **data):
        worker = self.request.hostname
        fields = data

        data = {
            "measurement": "action_stat",
            "tags": {
                "project": project,
                "action": action,
                "worker": worker,
            },
            "time": datetime.now(),
            "fields": fields
        }
        self.logger.info(u'统计回报 %s', data)
        self.influx_stat.write_points([data])

    def exec_jscode(self, action, conf, **kwargs):
        url = kwargs.get('url', 'http://__dummy_url__/')
        fdata = kwargs.pop('form', None)
        ndata = kwargs.pop('data', None)
        environ = {
            'form': fdata or {},
            'data': ndata or {}
        }
        # if url:
        #     prep = prepare(url, kwargs)
        # else:
        #     prep = prepare('http://__dummy_url__/', kwargs)
        jscode = conf['jscode']
        kwargs['timeout'] = conf['timeout']
        req = Request(url, **kwargs)
        preq = req.prepare()

        p = DuplexPhantomjs(self.send_message)
        try:
            p.prepare(preq, kwargs, jscode=jscode, environ=environ)
            data = p.run()
            return_message = None
            if data:
                resp = data.pop('resp', {})

                new_cookies = {}
                cookies = resp.get('cookies')
                if cookies:
                    for cookie in cookies:
                        new_cookies[cookie['name']] = cookie['value']

                    cks = data.setdefault('cookies', {})
                    new_cookies.update(cks)
                    data['cookies'] = new_cookies

                resp.update({
                    'elapsed': p.runtime
                })
                self.save_page(resp)
                return_message = data.get('message')
            self.logger.info(u'JS脚本返回: %s', return_message)
        except PhantomjsTimeout:
            # if len(p.results):
            #     data = p.results.pop()
            # else:
            data = {
                'status': 'EXC',
                'data': {},
                'message': u'JS脚本执行超时'
            }
            self.logger.error(u'JS脚本执行超时')
        except Exception:
            data = {
                'status': 'EXC',
                'data': {

                },
                'message': u'JS脚本执行异常'
            }
            self.logger.exception(u'JS脚本执行异常')

        if p.messages:
            self.logger.info('JsCode: %s', '; \n'.join(p.messages))
        return data

    def exec_pycode(self, action, conf, **kwargs):
        __TEMP_DATA__ = {}

        def _download(*a, **kw):
            resp = download(*a, **kw)
            __TEMP_DATA__.update({'__resp__': resp})
            return resp

        def set_next_action(action, data, **kw):
            return set_result('NXA', data, action=action, **kw)

        def set_next_form(form, data, **kw):
            return set_result('NXF', data, form=form, **kw)

        def set_result(status, data, **kw):
            result = kw.copy()
            # result['type'] = kw.get('type', 'result')
            result['status'] = status
            result['data'] = data
            result.setdefault('message', 'OK')
            # result['message'] = kw.get('message')
            resp = __TEMP_DATA__.get('__resp__')
            cookies = result.pop('cookies', None)
            if isinstance(cookies, CookieJar):
                cookies = dict_from_cookiejar(cookies)
            if isinstance(resp, Response):
                # result['url'] = resp.url
                # result['status_code'] = resp.status_code
                # result['reason'] = resp.reason
                rcs = dict_from_cookiejar(resp.cookies)
                if cookies:
                    rcs.update(cookies)
                cookies = rcs
                # result['content'] = resp.text
            if resp is not None:
                self.save_page(resp)

            if cookies:
                result['cookies'] = cookies

            __TEMP_DATA__.update({'__result__': result})
            return result

        pycode = conf['pycode']
        fdata = kwargs.pop('form', None)
        ndata = kwargs.pop('data', None)
        ENV = {
            'form': fdata or {},
            'data': ndata or {},
            # 'kwargs': kwargs
        }
        env = {
            # 'task_id': task_id,
            # 'action': action,
            # 'sitecode': sitecode,
            'get_connection': get_connection,
            'download': _download,
            'send_message': self.send_message,
            'set_result': set_result,
            'set_next_action': set_next_action,
            'set_next_form': set_next_form,
            # 'kwargs': kwargs,
            'logger': self._inner_logger,
            'environ': ENV
        }

        result = None
        # mod = compile_code(pycode, env)
        # func = mod.get(action, None)
        # # print 'mod => ', dir(mod)
        # if not func and '__entry__' in mod:
        #     func = mod['__entry__']
        #     if isinstance(func, six.string_types):
        #         func = mod.get(func, None)
        try:
            func = get_function(pycode, action, env)
            # print func
            if func:
                data = func()
                if isinstance(data, (tuple, list)) and len(data) == 2:
                    status, data = data
                    set_result(status, data)
                elif data:
                    set_result('OK', data)

                result = __TEMP_DATA__.get('__result__')

                self.logger.info(u'Py执行成功 Result: %s', saferepr(result, 128))
            else:
                result = {
                    'status': 'ERR',
                    'data': {},
                    'message': u'找不到Py入口方法'
                }
                self.logger.error(u'找不到Py入口方法')
        except Exception:
            result = {
                'status': 'EXC',
                'data': {},
                'message': u'动作执行异常'
            }
            self.logger.exception(u'执行Py异常')

        if result is None:
            result = {
                'status': 'EXC',
                'data': {},
                'message': u'Py脚本返回值为空'
            }
            self.logger.error(u'Py脚本返回值为空')

        # if 'cookies' in result:
        #     if isinstance(result['cookies'], CookieJar):
        #         result['cookies'] = dict_from_cookiejar(result['cookies'])

        return result


@app.task(bind=True, base=ActionTask, name='xspider.action')
def action(self, project, name, **kwargs):
    batch_id = kwargs.get('batch_id')
    cnf = xconf.get_action(project, name)
    lang = cnf['lang']
    if lang == 1:
        result = self.exec_pycode(name, cnf, **kwargs)
    elif lang == 0:
        result = self.exec_jscode(name, cnf, **kwargs)
    else:
        result = {
            'status': 'EXC',
            'data': {},
            'message': u'找不到执行入口. Action 设置错误 [%s]' % (batch_id, )
        }
        self.logger.error(u'找不到执行入口. Action [%s/%s/%s] 设置错误' % (project, name, batch_id))

    # if isinstance(result, dict):
    #     result.setdefault('status', 'OK')
    #     result.setdefault('data', {})
    #     result.setdefault('message', '')

    # if result and not isinstance(result, dict):
    #     result = {
    #         'type': 'OK',
    #         'data': result,
    #     }
    # else:
    #     result = {
    #         'status': 'ERR',
    #         'data': {},
    #         'message': u'执行结果为空 %s' % result,
    #     }
    #     self.logger.error(u'执行结果为空 result=%s / %s', result, type(result))

    result.setdefault('status', 'OK')
    result.setdefault('data', {})
    result.setdefault('message', '')
    result['task'] = {
        'project': project,
        'batch_id': batch_id,
        'action': name
    }
    if '__deep__' in kwargs:
        result['__deep__'] = kwargs['__deep__']
    # if kwargs.get('include_content') is not True:
    #     result.pop('content', '')
    #     result.pop('headers', '')
    return result
