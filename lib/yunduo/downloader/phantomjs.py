# coding=utf8

import time
import random
import os.path
import select
import errno
import subprocess
import json
from collections import defaultdict
from six.moves.urllib.parse import urlparse
from six.moves.http_cookiejar import CookieJar
from conf.common import HTTP_DEFAULT_HEADERS, HTTP_TIMEOUT
# from requests import Response
from requests.cookies import create_cookie
# from mergedict import ConfigDict
# from celery.utils.encoding import str_to_bytes, bytes_to_str
# from xspider.app import app
from yunduo.utils import merge
from yunduo.utils.functional import str_encode
from yunduo.downloader.models import Response

PYPHANTOMJS_ROOT = "%s/phantomjslib" % os.path.dirname(os.path.realpath(__file__))
PYPHANTOMJS_BIN = "%s/phantomjs" % PYPHANTOMJS_ROOT
PYPHANTOMJS_CONF = "--config=%s/config.json" % PYPHANTOMJS_ROOT


class PhantomjsTimeout(Exception):
    pass


class Phantomjs(object):

    def __init__(self):
        self.fd2file = {}
        self.fd2output = defaultdict(str)
        self.input = ''
        self.poller = None
        self.proc = None
        self.proc_args = None
        self.timeout = HTTP_TIMEOUT * 2
        self.results = []
        self.messages = []
        self.runtime = 0

    def prepare(self, preq, kwargs=None, **kw):
        if not kwargs:
            kwargs = {}
        kwargs.update(kw)
        if preq is None and not kwargs.get('jscode'):
            raise Exception(u'prep and jscode, one of which must be set')

        args = [PYPHANTOMJS_BIN, PYPHANTOMJS_CONF, '--load-images=true']
        # if 'proxies' in kwargs and kwargs['proxies']:
        if preq.proxies:
            proxy_dict = preq.proxies
            proxy_http = proxy_dict.get('https')
            proxy_https = proxy_dict.get('http')
            proxy_cred = urlparse(proxy_https or proxy_http)
            if proxy_cred.port:
                args.append('--proxy=%s:%s' %
                            (proxy_cred.hostname, proxy_cred.port))
            else:
                args.append('--proxy=%s' % proxy_cred.hostname)
            args.append('--proxy-type=%s' % proxy_cred.scheme.lower())
            if proxy_cred.username:
                args.append('--proxy-auth=%s:%s' %
                            (proxy_cred.username, proxy_cred.password))

        script = None
        if 'script_file' in kwargs:
            script = kwargs['script_file']
            if not os.path.exists(script):
                script = os.path.join(PYPHANTOMJS_ROOT, script)
                if not os.path.exists(script):
                    script = None

        if not script:
            script = "%s/bootstrap.js" % PYPHANTOMJS_ROOT

        args.append(script)
        args.append('--casper-path=%s/modules' % PYPHANTOMJS_ROOT)
        # print (args)
        self.proc_args = args
        settings = {}

        headers = dict(preq.headers)
        if 'Accept-Encoding' in preq.headers:
            val = preq.headers['Accept-Encoding']
            if val and 'gzip' in val:
                f = filter(lambda e: e and e.strip() != 'gzip', val.split(','))
                headers['Accept-Encoding'] = ','.join(list(f))
        settings = {
            'method': preq.method,
            'headers': headers,
            'data': preq.body
        }

        self.timeout = kwargs.get('timeout', self.timeout)
        options = merge({'waitTimeout': kwargs.get('waitTimeout', self.timeout) * 1000,
                         'timeout': self.timeout * 1000}, kwargs.get('options', {}))

        self.input = json.dumps({
            'options': options,
            'url': preq.url if preq.url != 'http://__dummy_url__/' else None,
            # 'timeout': self.timeout,
            'settings': settings,
            'environ': kwargs.get('environ'),
            'jscode': kwargs.get('jscode')
        }).encode('utf8')

        # if self.poller and self.proc:
        #     self.poll_register(self.proc.stdin, select.POLLOUT)

    def poll_register(self, file_obj, eventmask):
        fd = file_obj.fileno()
        self.poller.register(fd, eventmask)
        self.fd2file[fd] = file_obj

    def poll_unregister(self, fd, close=False):
        self.poller.unregister(fd)
        file = self.fd2file.pop(fd, None)
        if file and close:
            file.close()

    def _process_data(self, fd):
        s = self.fd2output[fd]
        if not s:
            return
        b = s.find('>>>\n\n')
        e = s.find('\n\n<<<')
        # print 'find b=%s, e=%s' % (b, e)
        if b > -1 and e > -1:
            c = s[b + 4:e]
            s = ''
            data = json.loads(c)
            self.fd2output[fd] = self.fd2output[fd][e + 4:]
            self.results.append(data)
            self.process(data)
        elif b > 0:
            # print fd2output[fd][:b]
            self.fd2output[fd] = self.fd2output[fd][b:]
        elif b == -1 and e == -1:
            # print '-=-=-NONE=%s' % self.fd2output[fd]
            self.messages.append(self.fd2output[fd])
            self.fd2output[fd] = ''

    def process(self, data):
        return data

    # def ontimeout(self):
    #     if self.proc:
    #         self.proc.kill()
    #         self.proc = None
    #     if self.poller and self.fd2file:
    #         for fd in self.fd2file:
    #             self.poll_unregister(fd)

    def run(self):
        start_time = time.time()
        self.poller = select.poll()
        _PIPE_BUF = getattr(select, 'PIPE_BUF', 512)
        input_offset = 0
        self.proc = subprocess.Popen(self.proc_args, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        if self.input:
            self.poll_register(self.proc.stdin, select.POLLOUT)
        self.poll_register(self.proc.stdout, select.POLLIN)
        timeout = self.timeout + 3
        try:
            # print self.fd2file
            # print self.proc.poll(), self.proc
            while self.fd2file:
                try:
                    ready = self.poller.poll(0.5)
                except select.error as e:
                    # print '---------------', e
                    if e.args[0] == errno.EINTR:
                        continue
                    raise

                # print ready
                for fd, mode in ready:
                    if mode & select.POLLOUT:
                        chunk = self.input[input_offset:input_offset + _PIPE_BUF]
                        try:
                            input_offset += os.write(fd, chunk)
                            # print 'write %s' % input_offset
                        except OSError as e:
                            if e.errno == errno.EPIPE:
                                self.poll_unregister(fd, True)
                            else:
                                raise
                        else:
                            if input_offset >= len(self.input):
                                # print 'write %s DONE' % input_offset
                                self.poll_unregister(fd, True)

                    elif mode & select.POLLIN:
                        data = os.read(fd, 4096)
                        if not data:
                            self.poll_unregister(fd)
                        else:
                            self.fd2output[fd] += str_encode(data, None)  # .decode('utf8')
                            # print 'IO Receive: ', data
                            self._process_data(fd)
                    elif mode & select.POLLHUP:
                        self.poll_unregister(fd, True)
                    else:
                        # Ignore hang up or errors.
                        # close_unregister_and_remove(fd)
                        print ('err', fd)
                        self.poll_unregister(fd, True)

                if time.time() - start_time > timeout:
                    raise PhantomjsTimeout()

            # print self.fd2file
            # print self.proc.poll(), self.proc
        finally:
            if self.proc and self.proc.poll() is None:
                self.proc.kill()
            self.proc = None
            if self.poller and self.fd2file:
                for fd in list(self.fd2file.keys()):
                    self.poll_unregister(fd)

        print('results len=%s' % len(self.results))
        self.runtime = time.time() - start_time
        if len(self.results):
            return self.results.pop()
        return None


def phantomjs_download(preq, **kw):
    p = Phantomjs()
    p.prepare(preq, kw)
    resp = Response()

    try:
        data = p.run()
        if data:
            # print '-=-=-=-=-=-=-=-=-', data['meta']
            rdata = data['resp']
            try:
                rdata['content'] = rdata['content'].encode('utf8')
            except Exception:
                pass

            cookies = rdata.get('cookies')
            if cookies:
                new_cookies = CookieJar()
                for cookie in cookies:
                    c = create_cookie(cookie['name'], cookie['value'], domain=cookie['domain'],
                                      path=cookie['path'], secure=cookie['secure'], expires=cookie['expiry'])
                    new_cookies.set_cookie(c)
                rdata['cookies'] = new_cookies

            resp = Response.from_dict(rdata)
            resp.meta = data['meta']
            # data = result.pop()
#             resp.url = data['url']
#             content = data.get('content', '')
#             try:
#                 content = content.encode('utf8')
#             except Exception:
#                 pass
#             status = data['type']
#             if status != 'result':
#                 # content = data['error']
#                 resp.status_code = data['status_code'] or 571
#                 resp.reason = data['reason']
#                 resp._content = content
#             else:
#                 resp.status_code = data['status_code']
#                 resp.reason = data['reason']
#                 resp._content = content
#                 cookies = data.get('cookies')
#                 if cookies:
# # {'domain': '.jd.com', 'name': '__jdb', 'expires': 'Wed, 05 Jul 2017 14:50:24 GMT', 'expiry': 1499266224,
# #  'value': '122270672.2.1499264397652469999225|1.1499264398', 'path': '/', 'httponly': False, 'secure': False}
# # version=0, name=name, value=value, port=None, domain='', path='/', secure=False, expires=None,
# # discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False,)
#                     for cookie in cookies:
#                         # cookie.pop('expiry', None)
#                         # cookie.pop('httponly', None)
#                         c = create_cookie(cookie['name'], cookie['value'], domain=cookie['domain'],
#                                           path=cookie['path'], secure=cookie['secure'], expires=cookie['expiry'])
#                         resp.cookies.set_cookie(c)
#             resp.encoding = 'utf-8'
#             resp._content_consumed = True
        else:
            resp.url = preq.url
            resp.status_code = 574
            resp.reason = 'phantomjs:return None'
            resp._content = ''
    except PhantomjsTimeout:
        print ('PhantomjsTimeout')
        # resp = Response()
        resp.status_code = 572
        resp.reason = 'phantomjs:exception:timeout'
        resp._content = ''

    # except Exception as exc:
    #     resp.status_code = 570
    #     resp.reason = 'exception: %s' % exc
    #     resp._content = ''
    #     logger.exception('content exception')
    print ('messages: %s' % ('\n---------\n'.join(p.messages)))
    return resp
