
import random
from requests import Session
# from mergedict import ConfigDict
from yunduo.utils import merge
from yunduo.conf import xconf  # HTTP_DEFAULT_HEADERS, HTTP_TIMEOUT
from .models import Request, Response
from .requests import requests_download
from .phantomjs import phantomjs_download, Phantomjs
from .proxy import get_proxy, feedback_proxy


TIMEOUT = xconf.get_http('timeout') or 10
DEFAULT_HEADERS = xconf.get_http('headers') or {}


def download(url, **kw):
    # print (kw)
    # preq = prepare(url, kw)
    # fs = ['method', 'headers', 'files', 'data', 'params', 'auth', 'cookies', 'hooks',
    #       'json', 'meta', 'proxy_type', 'proxies', 'cookie_type']
    # rkw = dict((key, kw.pop(key, None)) for key in fs)
    before_request = kw.pop('before_request', None)
    after_response = kw.pop('after_response', None)
    headers = kw.pop('headers', {})
    kw['headers'] = merge(DEFAULT_HEADERS, headers)

    req = Request(url, **kw)
    preq = req.prepare()

    if preq.proxy_type and not preq.proxies:
        preq.proxies = get_proxy(preq.proxy_type)

    if before_request:
        before_request(preq)
    # use_proxy = kw.pop('proxy_type', False)
    # proxy = None
    # if use_proxy != '0':
    #     proxy = get_proxy(url)
    #     if proxy:
    #         kw['proxies'] = proxy
    # if preq.proxy_type:
    #     if not preq.proxies:
    #         if preq.proxy_type is True:
    #             proxy = get_proxy(url)
    #         else:
    #             proxy = get_proxy(url, preq.proxy_type)
    #         preq.proxies = kw['proxies'] = proxy

    kkw = {
        'proxies': preq.proxies,
        'timeout': kw.get('timeout', TIMEOUT)
    }

    # print 'preq.headers %s' % (preq.headers)
    try:
        js_enabled = kw.pop('js_enable', False)
        if js_enabled:
            jsto = kw.pop('js_timeout', None)
            if jsto:
                kkw['timeout'] = jsto
            resp = phantomjs_download(preq, **kkw)
        else:
            # dkw = {
            #     'timeout': kw['timeout']
            # }
            # if preq.proxies:
            #     dkw['proxies'] = preq.proxies
            resp = requests_download(preq, **kkw)
            # setattr(resp, 'meta', {})

        # if proxy:
        #     status = resp.status_code == 200 and 'succ' or 'fail'
        #     resp.headers['X-HTTP-PROXY'] = proxy
        status = 'succ' if resp.status_code in (200, 572) else 'fail'
        if after_response:
            after_response(resp)
        return resp
    except Exception:
        status = 'exc'
        # print(repr(preq), repr(preq.headers))
        raise
    # finally:
    #     if preq.proxy_type and preq.proxies:
    #         feedback_proxy(preq.proxy_type, preq.proxies, status)
