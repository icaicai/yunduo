
import six
import cchardet as chardet
from copy import deepcopy
from datetime import timedelta
from requests import models
from requests.compat import str
from requests.utils import dict_from_cookiejar, cookiejar_from_dict
from requests.structures import CaseInsensitiveDict
from celery.utils.encoding import str_to_bytes
from yunduo.utils import merge


def response_to_dict(resp):
    data = {
        'url': resp.url,
        'content': resp.text,
        'status_code': resp.status_code,
        'encoding': resp.encoding,
        'reason': resp.reason,
        'elapsed': resp.elapsed.total_seconds()
    }

    if resp.headers:
        data['headers'] = dict(resp.headers)

    if hasattr(resp, 'meta'):
        data['meta'] = resp.meta
    if resp.history:
        hs = []
        for h in resp.history:
            h.history = []
            hs.append(response_to_dict(h))
        data['history'] = hs

    if resp.cookies:
        data['cookies'] = dict_from_cookiejar(resp.cookies)

    if resp.request:
        r = resp.request
        req = data['request'] = {}
        req['method'] = r.method
        req['url'] = r.url
        if r.headers:
            req['headers'] = dict(r.headers)
        if r.body:
            req['data'] = r.body
        for attr in ('meta', 'proxy_type', 'proxies', 'cookie_type'):
            req[attr] = getattr(r, attr, None)

    return data


def dict_to_response(data):
    if isinstance(data, Response):
        return data
    resp = Response()
    resp._content_consumed = True
    if isinstance(data, six.string_types):
        resp._content = str_to_bytes(data)
        resp.url = 'http://__from_string__/'
        resp.status_code = 220
        resp.reason = 'String to Response'
    else:
        resp._content = data.get('content')
        resp.status_code = data.get('status_code')
        if 'headers' in data:
            resp.headers = CaseInsensitiveDict(data['headers'])
        resp.url = data.get('url', 'http://__empty_url__/')
        if 'history' in data and data['history']:
            hs = []
            for h in data['history']:
                hs.append(dict_to_response(h))
            resp.history = hs
        resp.encoding = data.get('encoding')
        resp.reason = data.get('reason')

        cookies = data.get('cookies')
        if cookies:
            if isinstance(cookies, dict):
                resp.cookies = cookiejar_from_dict(cookies)
            else:
                resp.cookies = cookies
        elapsed = data.get('elapsed')
        if isinstance(elapsed, (int, float)):
            elapsed = timedelta(seconds=elapsed)
        resp.elapsed = elapsed
        req = data.get('request')
        if req:
            preq = PreparedRequest()
            preq.prepare(**req)
            resp.request = preq
    return resp


class PreparedRequest(models.PreparedRequest):

    def __init__(self):
        super(PreparedRequest, self).__init__()
        self.meta = None
        self.proxy_type = None
        self.proxies = None
        self.cookie_type = None

    def prepare(self, method=None, url=None, headers=None, files=None, data=None, params=None,
                auth=None, cookies=None, hooks=None, json=None, meta=None, **kw):
        if meta is not None:
            self.meta = deepcopy(meta)
        self.proxies = kw.get('proxies')
        self.prepare_proxy(kw.get('proxy_type'))
        self.cookie_type = kw.get('cookie_type')
        super(PreparedRequest, self).prepare(method, url, headers, files, data, params, auth,
                                             cookies, hooks, json)

    def prepare_proxy(self, proxy_type):
        if isinstance(proxy_type, six.string_types):
            self.proxy_type = proxy_type
        else:
            self.proxy_type = bool(proxy_type)
            if self.proxy_type:
                self.proxies = None

    def prepare_headers(self, headers):
        default_headers = {}
        if headers:
            default_headers.update(headers)

        headers = default_headers
        super(PreparedRequest, self).prepare_headers(headers)

    def copy(self):
        p = super(PreparedRequest, self).copy()
        if self.meta is not None:
            p.meta = deepcopy(self.meta)

        return p


class Request(models.Request):

    def __init__(self, url=None, method='GET', headers=None, files=None, data=None,
                 params=None, auth=None, cookies=None, hooks=None, json=None, **kw):
        self.meta = kw.pop('meta', None)
        self.proxy_type = kw.pop('proxy_type', None)
        self.proxies = kw.pop('proxies', None)
        self.cookie_type = kw.pop('cookie_type', None)
        super(Request, self).__init__(method, url, headers, files, data,
                                      params, auth, cookies, hooks, json)

    def prepare(self):
        p = PreparedRequest()
        p.prepare(
            method=self.method,
            url=self.url,
            headers=self.headers,
            files=self.files,
            data=self.data,
            json=self.json,
            params=self.params,
            auth=self.auth,
            cookies=self.cookies,
            hooks=self.hooks,
            meta=self.meta,
            proxy_type=self.proxy_type,
            proxies=self.proxies,
            cookie_type=self.cookie_type
        )

        return p


class Response(models.Response):
    __attrs__ = [
        '_content', 'status_code', 'headers', 'url', 'history',
        'encoding', 'reason', 'cookies', 'elapsed', 'request'
    ]

    def __init__(self):
        super(Response, self).__init__()
        self._meta = None
        self.use_proxy = None
        self.proxies = None

    @property
    def meta(self):
        m = {}
        meta = getattr(self.request, 'meta', None)
        if meta:
            merge(m, meta)
        if self._meta:
            merge(m, self._meta)
        return m

    @meta.setter
    def meta(self, meta):
        self._meta = meta

    @property
    def apparent_encoding(self):
        """The apparent encoding, provided by the chardet library"""
        return chardet.detect(self.content)['encoding']

    @property
    def text(self):
        # Try charset from content-type
        encoding = self.encoding

        if not self.content:
            return str('')

        # Fallback to auto-detected encoding.
        if encoding is None or encoding.startswith('ISO-8859-'):
            encoding = self.apparent_encoding

        # Decode unicode from given encoding.
        try:
            content = str(self.content, encoding, errors='replace')
        except (LookupError, TypeError):
            content = str(self.content, errors='replace')

        return content

    def close(self):
        if self.raw is None:
            return
        super(Response, self).close()

    def to_dict(self):
        return response_to_dict(self)

    @classmethod
    def from_dict(cls, data):
        return dict_to_response(data)

    @classmethod
    def from_response(cls, resp):
        if not resp._content_consumed:
            resp.content

        this = cls()
        for attr in cls.__attrs__:
            setattr(this, attr, getattr(resp, attr, None))
        setattr(this, '_content_consumed', True)
        setattr(this, 'raw', None)

        return this




# class _WrappedResponse(object):
#     def __init__(self, rsp, meta=None):
#         self._meta = meta
#         self._rsp = rsp
#         self._req = rsp.request

#     def __getattr__(self, attr):
#         return getattr(self._rsp, attr)

#     @property
#     def meta(self):
#         meta = getattr(self._req, 'meta', None)
#         if not meta:
#             meta = {}
#         if self._meta:
#             meta.update(self._meta)
#         return meta

#     @meta.setter
#     def meta(self, val):
#         self._meta = val


# def wrapper_response(resp, meta=None):
#     return _WrappedResponse(resp, meta)




