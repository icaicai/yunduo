# coding=utf8

import time
import json
import six
from datetime import datetime
from w3lib.url import parse_url
from kombu.entity import Exchange, Queue
# from phantomjs import phantomjs_download
from requests.utils import dict_from_cookiejar
from yunduo.dupefilter import Dupefilter
from yunduo.errors import DenyError, ConfigError, DownloadError
from yunduo.parser.htmlextractor import Link, Extractor, ItemResult
# from conf.common import HTTP_MAX_RETRIES, HTTP_RETRY_CODE
from yunduo.conf import xconf
# from connections import redis_conf, influx_stat, mongo_page
from yunduo.utils import merge, arg_to_iter
from yunduo.code import compile, get_function, get_script
from yunduo.downloader import download, proxy as proxy_mod
# from connections import get_connection
from yunduo.resource import get_connection
from xspider.jobaction import JobAction
from xspider.app import app
# from xspider.log import get_task_logger
# from xspider.job import gen_queue_name
from .base import StrategyTask

redis_run = get_connection('run')
# 'queue', 'routing_key', 'exchange', 'priority', 'expires',
# 'serializer', 'delivery_mode', 'compression', 'time_limit',

class CrawlTask(StrategyTask):
    # 定义自己的策略
    # Strategy = 'xspider.strategy:default'
    # rate_limit = True
    # counter = True
    # store_info = True
    # custom_queue = True

    # def __init__(self):
    #     super(CrawlTask, self).__init__()
    #     self.df = Dupefilter()
    #     self._exchange = Exchange('xcrawl', type='direct')

    def initialize(self):
        super(CrawlTask, self).initialize()
        # self.logger = get_task_logger(self.name)
        self.df = Dupefilter()
        # self.exchange = Exchange('xcrawl', type='direct')
        # self.HTTP_MAX_RETRIES = conf.get_http('max_retries')
        self.influx_stat = get_connection('stat')
        self.http_max_retries = xconf.get_http('max_retries')
        self.http_retry_codes = xconf.get_http('retry_codes')

    def brief(self, args=None, kwargs=None):
        req = self.request
        if not req and not args:
            return {}

        args = args or req.args
        kwargs = kwargs or (req and req.kwargs) or {}

        info = {
            'project': args[0],
            'job': args[1],
            'page': args[2],
            'url': args[3],
            'batch_id': kwargs.get('batch_id')
        }

        return info

    def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
                    link=None, link_error=None, shadow=None, **options):
        super(CrawlTask, self).apply_async(args, kwargs, task_id, producer, link, link_error, shadow, **options)
        # count++
        if not args:
            arg = self.request.args
        else:
            arg = args
        project = arg[0]
        job = arg[1]
        page = arg[2]
        batch_id = (kwargs or self.request.kwargs).get('batch_id')

        self._incr_task(project, job, page, batch_id, 1)

    # def on_success(self, retval, task_id, args, kwargs):
    #     pass

    # def on_failure(self, exc, task_id, args, kwargs, einfo):
    #     pass

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        project = args[0]
        job = args[1]
        page = args[2]
        batch_id = kwargs.get('batch_id')
        self._desc_task(project, job, page, batch_id, 1)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if len(args) < 1:
            return

        project = args[0]
        job = args[1]
        page = args[2]
        batch_id = kwargs.get('batch_id')
        self._desc_task(project, job, page, batch_id, 1)

    def _incr_task(self, project, job, page, batch_id, n):
        c_key = 'counter:%s' % project
        c_suffix = batch_id
        with redis_run.pipeline() as pipe:
            pipe.hget(c_key, 'r_%s' % (c_suffix,))
            pipe.hincrby(c_key, 'r_%s' % (c_suffix,), n)
            pipe.hincrby(c_key, 'q_%s' % (c_suffix,), n)
            vals = pipe.execute()
            # print('_incr_task', vals)
            if (not vals[0] or int(vals[0]) == 0) and vals[1]:
                started_time = time.time()
                queue_name = 'xcrawl:%s:%s:%s' % (project, job, batch_id)
                pipe.hset(c_key, 'started%s' % c_suffix, started_time)
                pipe.hset('queue:running', queue_name, time.time())
                pipe.hset('project:running', project, queue_name)
                pipe.execute()
                self.logger.info(u'Job开始')

                # data = self.brief()
                data = {
                    'project': project,
                    'job': job,
                    'page': page,
                    # 'url': args[3],
                    'batch_id': batch_id,
                    'type': 'job-started',
                    'task_id': self.request.id if self.request else '',
                    'started_time': started_time
                }
                app.send_notify('job-started', data)

    def _desc_task(self, project, job, page, batch_id, n):
        c_key = 'counter:%s' % project
        c_suffix = batch_id
        with redis_run.pipeline() as pipe:
            pipe.hincrby(c_key, 'f_%s' % (c_suffix,), n)
            pipe.hincrby(c_key, 'q_%s' % (c_suffix,), -n)
            vals = pipe.execute()
            # print('_desc_task', vals)
            if vals[0] and vals[1] == 0:
                # print '===send_event project-finished %r' % redis_run.hgetall(key)
                fs = ['started%s' % c_suffix, 'r_%s' % c_suffix, 'f_%s' % c_suffix, 'q_%s' % c_suffix]
                queue_name = 'xcrawl:%s:%s:%s' % (project, job, batch_id)
                pipe.hmget(c_key, fs)
                pipe.hdel(c_key, *fs)

                pipe.hdel('queue:running', queue_name)
                pipe.hdel('project:running', project)
                vals = pipe.execute()
                data = {
                    'started': float(vals[0][0]),
                    'r': vals[0][1],
                    'f': vals[0][2],
                    'finished': time.time()
                }

                runtime = data['finished'] - data['started']
                self.logger.info(u'Job完成 r: %s, f: %s, elapsed: %s', data['r'], data['f'], runtime)
                # task_on_all_finished(data)

                # data = self.brief()
                data = {
                    'project': project,
                    'job': job,
                    'page': page,
                    'batch_id': batch_id,
                    'type': 'job-finished',
                    'task_id': self.request.id if self.request else '',
                    'elapsed_time': runtime
                }
                app.send_notify('job-finished', data)

    def get_proxy(self, type_=None):
        return proxy_mod.get_proxy(type_)

    def feedback_proxy(self, proxy, status):
        return proxy_mod.feedback_proxy(proxy, status)

    def get_cookies(self, site):
        pass

    def set_cookies(self, site, cookies):
        pass

    def pause_job(self, project, job, batch_id, reason=None):
        ja = JobAction(project, job, batch_id)
        ja.pause()
        self.logger.info('任务暂停. Reason: %s', reason)

    def report_stat(self, **kw):
        req = self.request
        worker = req.hostname
        args = req.args
        kwargs = req.kwargs
        host = kw.pop('hostname', '')
        url = kw.pop('url', '')
        if not host and url:
            try:
                host = parse_url(url).hostname
            except Exception:
                host = ''
        fields = kw

        data = {
            "measurement": "crawl_stat",
            "tags": {
                "project": args[0],
                "job": args[1],
                "page": args[2],
                "host": host,
                "worker": worker,
                "batch_id": kwargs.get('batch_id')
            },
            "time": datetime.now(),
            "fields": fields
        }
        # self.logger.info(u'统计回报 %s', data)
        try:
            self.influx_stat.write_points([data])
        except Exception:
            self.logger.exception('统计回报异常')

    def compile(self, code, env=None, **kw):
        info = self.brief()
        try:
            env = env or {}
            environ = env.setdefault('environ', {})
            environ.update(info)
            return compile(code, env, **kw)
        except Exception:
            self.logger.exception(u'代码编译异常 %s', code)

        return {}

    def fetch(self, stat_data, url, **conf):
        try:
            before_request = conf.get('before_request')
            after_response = conf.get('after_response')

            if before_request or after_response:
                info = self.brief()
                env = {
                    # 'send_notify': _send_notify,
                    # 'Link': Link,
                    # 'Extractor': Extractor,
                    # 'ItemResult': ItemResult,
                    'get_connection': get_connection,
                    'DenyError': DenyError,
                    # 'crawl': _crawl,
                    # 'download': _download,
                    'dprint': lambda *args, **kw: None,
                    'environ': info.copy()
                }
                if before_request:
                    conf['before_request'] = get_function(before_request, 'before_request', env)

                if after_response:
                    conf['after_response'] = get_function(after_response, 'after_response', env)
            # pt = conf.get('proxy_type')
            # if pt and not conf.get('proxies'):
            #     conf['proxies'] = self.get_proxy()
            resp = download(url, **conf)
        except Exception as exc:
            stat_data['f_0'] = 1
            self.logger.exception(u'下载异常 %s Retries=%s', url, self.request.retries)
            raise DownloadError(str(exc))
        else:
            stat_data['f_%s' % resp.status_code] = 1
            # stat_data['f_2'] = 1
            return resp

    def check_deny(self, resp, **conf):
        code = conf.get('deny_code')
        text = conf.get('deny_text')
        script = conf.get('deny_script')

        if code and resp.status_code in code:
            raise DenyError('检测到反爬特征状态码: %s' % resp.status_code)

        if text:
            resp_text = resp.text
            for txt in text:
                if txt in resp_text:
                    raise DenyError('检测到反爬特征文本: %s' % txt)

        info = self.brief()

        def _pause():
            ja = JobAction(info['project'], info['job'], info['batch_id'])
            ja.pause()

        def _stop():
            ja = JobAction(info['project'], info['job'], info['batch_id'])
            ja.stop(delete=False)

        if script:
            env = {
                'get_connection': get_connection,
                'job_pause': _pause,
                'job_stop': _stop,
                'send_message': self.send_message
            }
            func = get_function(script, 'is_deny', env)
            if func and func(resp):
                raise DenyError('检测到反爬特征（Script）')

        return False

    def parse(self, stat_data, resp, **conf):
        links = []

        def _crawl(page, url=None, **kw):
            if isinstance(page, Link):
                links.append(page)
            elif url:
                lnk = Link(page, url, **kw)
                links.append(lnk)

        def _download(url, **kw):
            ic = kw.pop('follow_cookie', True)
            if ic:
                cks = dict_from_cookiejar(resp.cookies)
                cookies = kw.setdefault('cookies', {})
                if cks:
                    cks.update(cookies)
                    kw['cookies'] = cks

            if resp.request and resp.request.proxies:
                kw['proxies'] = resp.request.proxies

            hdrs = kw.setdefault('headers', {})
            # if resp.request:
            #     hs = dict(resp.request.headers)
            #     hs.update(hdrs)
            #     kw['headers'] = hs
            hdrs.setdefault('Referer', resp.url)
            return download(url, **kw)

        item_type = conf.get('item_type')
        item_fields = conf.get('item_fields')
        item_pycode = conf.get('item_pycode')

        link_type = conf.get('link_type')
        link_rules = conf.get('link_rules')
        link_pycode = conf.get('link_pycode')

        encoding = conf.get('encoding')
        if not encoding:
            encoding = None

        info = self.brief()
        env = {
            # 'send_notify': _send_notify,
            'Link': Link,
            'Extractor': Extractor,
            'ItemResult': ItemResult,
            # 'BlockedError': BlockedError,
            'crawl': _crawl,
            'download': _download,
            'dprint': lambda *args, **kw: None,
            'environ': {
                'project': info['project'],
                'job': info['job'],
                'page': info['page'],
                'url': info['url'],
                'batch_id': info['batch_id'],
                'meta': resp.meta
            }
        }
        exor = None
        data = None
        urls = None
        if item_type in ('conf', 'code'):
            try:
                if item_type == 'conf' and item_fields:
                    exor = Extractor(resp, encoding)
                    data = exor.extract_items(item_fields)
                elif item_type == 'code' and item_pycode:
                    genv = self.compile(item_pycode, env)
                    extr_items = genv.get('extract_items')
                    conf_items = genv.get('conf_items')
                    if extr_items and callable(extr_items):
                        data = extr_items(resp)
                    elif conf_items:
                        exor = Extractor(resp, encoding)
                        data = exor.extract_items(conf_items)

            except Exception:
                stat_data['p_20'] = 0
                self.logger.exception(u'解析数据出错')
            else:
                if data:
                    if isinstance(data, ItemResult):
                        data, miss_fields, miss_rate = data
                    elif isinstance(data, (tuple, list)) and len(data) == 3:
                        data, miss_fields, miss_rate = data
                    else:
                        miss_fields, miss_rate = None, 0
                    if miss_fields:
                        # ms_num = len(missing)
                        # stat_data['p_913'] = len(miss_fields)
                        stat_data['p_24'] = miss_rate
                        self.logger.warning(u'数据缺失 %s %s %s', miss_fields, miss_rate, resp.url)
                    # else:
                    #     stat_data['p_221'] = 0

                    if isinstance(data, (list, tuple)):
                        stat_data['p_22'] = len(data)
                    else:
                        stat_data['p_22'] = 1

                    self.logger.info(u'解析出数据: %s', stat_data['p_22'])
                else:
                    stat_data['p_21'] = 1
                    self.logger.error(u'没有解析出数据')

        if link_type in ('conf', 'code'):
            try:
                if link_type == 'conf' and link_rules:
                    if not exor:
                        exor = Extractor(resp, encoding)
                    urls = exor.extract_links(link_rules)
                    # urls = self.parse_link_by_conf(resp, links['rules'])
                elif link_type == 'code' and link_pycode:
                    genv = self.compile(link_pycode, env)
                    extr_links = genv.get('extract_links')
                    conf_links = genv.get('conf_links')
                    if extr_links and callable(extr_links):
                        urls = extr_links(resp)
                    elif conf_links:
                        if not exor:
                            exor = Extractor(resp, encoding)
                        urls = exor.extract_links(conf_links)
            except Exception:
                stat_data['pc_30'] = 0
                self.logger.exception(u'抽取链接错误')
            else:
                if urls:
                    if not isinstance(urls, (list, tuple)):
                        urls = [urls]

        if urls:
            links.extend(urls)

        if links:
            stat_data['p_32'] = len(links)
            self.logger.info(u'抽取出链接: %s', stat_data['p_32'])
        elif link_type in ('conf', 'code'):
            stat_data['pc_31'] = 0
            self.logger.warning(u'没有抽取到链接')

        return data, links

    def add_link(self, lnk, conf):
        req = self.request
        args = req.args
        kwargs = req.kwargs
        project = args[0]
        job = args[1]

        if not isinstance(lnk, Link):
            return False

        kw = {
            'incr_mode': conf.get('incr_mode', False),
            'batch_id': kwargs.get('batch_id'),
            'df_query_only': conf.get('df_query_only'),
            'df_query_remove': conf.get('df_query_remove')
        }

        if self.df.seen(project, job, lnk, **kw):
            return False

        rate_limit = conf.get('rate_limit')
        # kwargs = self.request.kwargs
        lconf = lnk.conf

        dkw = kwargs.copy()
        dkw.pop('lconf', None)
        dkw['lconf'] = lconf
        if rate_limit:
            dkw['__limit__'] = rate_limit

        self.send_task('xspider.crawl', (project, job, lnk.page, lnk.url), dkw)
        # p_931 += 1
        return True

    def save_result(self, data, script, meta):
        # args = self.request.args
        req = self.request
        args = req.args
        kwargs = req.kwargs.copy() if req.kwargs else {}
        kwargs.pop('lconf', None)
        kw = {
            'meta': meta,
            'project': args[0],
            'job': args[1],
            'page': args[2],
            'url': args[3],
            'batch_id': kwargs.get('batch_id'),
            'task_id': req.id,
            'task_name': self.name,
            'created': datetime.now(),
            'kwargs': kwargs
        }
        # script = conf.get('item_save_script')
        self.send_task('save_result', (script, data), kw)
        if isinstance(data, dict):
            num = 1
        else:
            num = len(data)
        self.logger.info('新增 %s 条数据 %s', num, script)

    def exec_script(self, project, job, page, **kwargs):
        '''用于批量加入任务'''
        conf = xconf.get_job(project, job)
        env = {
            # 'send_notify': _send_notify,
            'get_connection': get_connection,
            'Link': Link,
            'Extractor': Extractor,
            'ItemResult': ItemResult,
            # 'BlockedError': BlockedError,
            # 'crawl': _crawl,
            # 'download': _download,
            'dprint': lambda *args, **kw: None,
            'environ': {
                'project': project,
                'job': job,
                'page': page,
                'url': None,
                'batch_id': kwargs.get('batch_id'),
                'meta': kwargs.get('meta')
            }
        }

        save_script = kwargs.get('save_script')
        meta = kwargs.get('meta')

        func = get_script(page, env, function=True, project=project)
        if func:
            pn_32 = 0
            pn_33 = 0
            result = func()
            # rate_limit = conf.get('rate_limit')
            result = arg_to_iter(result)

            for item in result:
                if isinstance(item, Link):
                    pn_32 += 1
                    if self.add_link(item, conf):
                        pn_33 += 1
                elif isinstance(item, dict):
                    self.save_result(item, save_script, meta)
            self.logger.info('新增链接 %s / %s', pn_33, pn_32)


@app.task(bind=True, base=CrawlTask, ignore_result=True, name='xspider.crawl')
def crawl(self, project, job, page, url, **kwargs):
    # print 'ID fetch self %s req %s' % (kwargs, id(self.request))
    if '__data__' in kwargs:
        ja = JobAction(project, job, kwargs.get('batch_id'))

        try:
            data = ja.get_data()
            if data:
                kwargs.update(data)
        except:
            pass
        kwargs.pop('__data__', None)

    if url is None:
        self.exec_script(project, job, page, **kwargs)
        return

    stat_data = {'t_9': 1}
    resp = None
    excd = False
    proxy_status = 'ok'
    batch_id = kwargs.get('batch_id')
    lconf = kwargs.get('lconf')
    page_save = None
    conf = {}
    try:
        conf = xconf.get_page(project, job, page)

        if lconf:
            conf = merge(conf, lconf)

        page_save = conf.get('save_page')
        item_type = conf.get('item_type')
        link_type = conf.get('link_type')
        save_script = kwargs.get('save_script', conf.get('save_script'))
        if not item_type and not link_type and not save_script:
            self.logger.error(u'页面配置错误',)
            raise ConfigError(u'页面配置错误, project=%s, job=%s, page=%s %s' % (project, job, page, conf))

        resp = self.fetch(stat_data, url, **conf)

        self.check_deny(resp, **conf)
        # blocked_code = conf.get('blocked_code')
        # if blocked_code and resp.status_code in blocked_code:
        #     raise BlockedError(retry=conf.get('blocked_retry', False))

        valid_code = tuple(conf.get('valid_code', ())) + (200, 572)

        if resp.status_code in valid_code:
            stat_data['p_12'] = 1
            resp_size = len(resp.content)
            stat_data['f_size'] = resp_size
            self.logger.info(u'下载完成 SIZE=%s URL=%s Retries=%s', resp_size, resp.url, self.request.retries)

            # blocked_text = conf.get('blocked_text')
            # if blocked_text:
            #     content = resp.content
            #     for txt in blocked_text:
            #         if txt in content:
            #             raise BlockedError(retry=conf.get('blocked_retry', False))

            if item_type or link_type:
                data, lnks = self.parse(stat_data, resp, **conf)
                if lnks:
                    incr_mode = conf.get('incr_mode', False)
                    cookie_type = conf.get('cookie_type')
                    cookies = conf.get('cookies')
                    hasnew = False
                    cnt, add = 0, 0
                    dfn = []
                    link_stats = {}
                    for lnk in lnks:
                        link_stats[lnk] = 0
                        cnt += 1
                        lconf = lnk.conf
                        if cookie_type == 'follow' and cookies:
                            lnk.add_cookies(cookies)
                        hdrs = lconf.setdefault('headers', {})
                        hdrs.setdefault('Referer', resp.url)

                        if lnk.df_enable:
                            if self.add_link(lnk, conf):
                                hasnew = True
                                add += 1
                                link_stats[lnk] = 1
                            # dfy.append(lnk)
                        # elif hasnew:
                        #     if self.add_link(lnk, conf):
                        #         add += 1
                        elif incr_mode:
                            dfn.append(lnk)
                        else:
                            if self.add_link(lnk, conf):
                                add += 1
                                link_stats[lnk] = 1

                    if incr_mode and hasnew and dfn:
                        for lnk in dfn:
                            if self.add_link(lnk, conf):
                                add += 1
                                link_stats[lnk] = 1

                    stat_data['p_33'] = add
                    links = '; '.join(["%s%s" % ('[N]' if v else '', k) for k, v in link_stats.items()])
                    self.logger.info(u'抽取链接: 新增 %s 总共 %s  Links: %s', add, cnt, links)

                if data:
                    # self.logger.info(u'抽取内容: %s', stat_data['p_23'])
                    self.save_result(data, save_script, resp.meta)

            elif save_script:
                self.save_result(resp, save_script, resp.meta)

        elif resp.status_code in (conf.get('http_retry_codes') or self.http_retry_codes):
            stat_data['p_11'] = 1
            self.logger.error(u'下载失败 %s [%s, %s] Retries=%s', resp.url, resp.status_code, resp.reason, self.request.retries)
            max_retries = conf.get('max_retries', self.http_max_retries)
            countdown = 2 ** self.request.retries
            raise self.retry(max_retries=max_retries, countdown=countdown)
        else:
            stat_data['p_14'] = 1
            self.logger.warning(u'未知的状态 [%s, %s]', resp.status_code, resp.reason)
    except DownloadError as exc:
        proxy_status = 'exc'
        max_retries = conf.get('max_retries', self.http_max_retries)
        countdown = 2 ** self.request.retries
        # self.logger.info('delivery_info => %s -- %s', self.request, self.request.delivery_info)
        raise self.retry(max_retries=max_retries, countdown=countdown, exc=exc)
    except DenyError as be:
        proxy_status = 'deny'
        excd = True
        stat_data['p_10'] = 1
        max_retries = conf.get('max_retries', self.http_max_retries)
        self.logger.error(u'解析失败: %s ; Retry=%s; Retries=%s/%s', str(be), be.retry, self.request.retries, max_retries)
        # if resp is not None and page_save == 1:
        #     self.save_page(project, page, resp, **kwargs)
        countdown = 2 ** self.request.retries
        raise self.retry(max_retries=max_retries, countdown=countdown, exc=be)
    except ConfigError as e:
        proxy_status = 'err'
        stat_data['t_1'] = 1
        self.pause_job(project, job, batch_id, '配置错误')
        six.reraise(type(e), e, e.__traceback__)
    except Exception as e:
        proxy_status = 'exc'
        excd = True
        stat_data['t_0'] = 1
        max_retries = conf.get('max_retries', self.http_max_retries)
        # if resp is not None and page_save == 1:
        #     self.save_page(project, page, resp, **kwargs)
        self.logger.exception(u'异常 %s', e)
        # six.reraise(type(e), e, e.__traceback__)
        countdown = 2 ** self.request.retries
        raise self.retry(max_retries=max_retries, countdown=countdown, exc=e)
    finally:
        if resp is not None:
            if resp.request and resp.request.proxies:
                self.feedback_proxy(resp.request.proxies, proxy_status)
            url = resp.url
            if page_save == 2 or excd and page_save == 1:
                self.save_page(resp, **kwargs)
        self.report_stat(url=url, **stat_data)
