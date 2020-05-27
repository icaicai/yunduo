# coding=utf8
import re
import six
import cchardet as chardet
from collections import namedtuple
from requests.compat import str as rstr
from requests.utils import dict_from_cookiejar
from requests.cookies import RequestsCookieJar
from kombu.utils.objects import cached_property
from celery.utils.saferepr import saferepr
from yunduo.parser.selector import Selector, SelectorList
from yunduo.utils import merge, arg_to_iter, no_default, make_hash, md5sum
from yunduo.code import get_function

ItemResult = namedtuple('ItemResult', ['data', 'miss_fields', 'miss_rate'])
_re_type = type(re.compile("", 0))
_matches = lambda url, regexs: any(r.search(url) for r in regexs)


def is_valid_url(url):
    try:
        return url.strip().split('://', 1)[0] in {'http', 'https', 'file'}
    except Exception:
        return False


# class BlockedError(Exception):
#
#     def __init__(self, retry=False, *args, **kwargs):
#         super(BlockedError, self).__init__(*args, **kwargs)
#         self.retry = retry


def _hash(obj):
    if obj is None:
        return hash(obj)

    if isinstance(obj, dict):
        obj.items()


class Link(object):
    """Link objects represent an extracted link by the LinkExtractor."""

    # __slots__ = ['url', 'page', 'conf', 'method', 'data', 'headers']

    def __init__(self, page, url, **kw):
        self.page = page
        self.url = url
        self.conf = kw
        # self.conf.setdefault('headers', {})
        cookies = self.conf.get('cookies')
        if cookies and isinstance(cookies, RequestsCookieJar):
            self.conf['cookies'] = dict_from_cookiejar(cookies)

    # @property
    # def method(self):
    #     return self.conf.get('method', 'GET')

    # @property
    # def meta(self):
    #     return self.conf.get('meta')

    # @property
    # def data(self):
    #     return self.conf.get('data')

    # @property
    # def params(self):
    #     return self.conf.get('params')

    # @property
    # def headers(self):
    #     return self.conf.get('headers')

    @property
    def df_enable(self):
        return self.conf.get('df_enable', True)

    # @property
    # def fingerprint(self):
    #     return md5sum('%s:%s:%s' % (self.page, self.url, md5sum(self.conf)))

    def add_cookies(self, cookies):
        oc = self.conf.get('cookies') or {}
        self.conf['cookies'] = merge(cookies, oc)

    def add_headers(self, headers):
        hdrs = self.conf.setdefault('headers', {})
        hdrs.update(headers)

    def __eq__(self, other):
        return self.url == other.url and self.page == other.page and \
            self.conf == other.conf

    def __hash__(self):
        return hash(self.page) ^ hash(self.url) ^ make_hash(self.conf)

    def __repr__(self):
        return 'Link(%r, %r, %s)' % (self.page, self.url, saferepr(self.conf, 128))


class Extractor(object):

    def __init__(self, resp, encoding=None, base_url=None):
        self.resp = resp
        self.encoding = encoding
        self.base_url = base_url

    @cached_property
    def sel(self):
        resp = self.resp
        if isinstance(resp, six.text_type):
            content = resp
        elif isinstance(resp, six.binary_type):
            content = resp
            if self.encoding:
                encoding = self.encoding
            else:
                encoding = chardet.detect(content)

            try:
                content = rstr(content, encoding, errors='replace')
            except (LookupError, TypeError):
                content = rstr(content, errors='replace')
        else:
            content = resp.text

        if not content:
            return None

        sel = Selector(content)
        doc = sel.root
        if self.base_url:
            doc.make_links_absolute(self.base_url)
        elif doc.base_url:
            doc.make_links_absolute(doc.base_url)
        elif getattr(resp, 'url', None):
            doc.make_links_absolute(resp.url)
        return sel

    @property
    def html(self):
        return self.sel.extract()

    def css(self, selector):
        return self.sel.css(selector)

    def xpath(self, xpath):
        return self.sel.xpath(xpath)

    def extract_items(self, fields):
        selobj = self.sel
        data = self._extract_items(fields, selobj)

        return data

    def _extract_items(self, fields, selobj=None):
        if selobj is None:
            selobj = self.sel
        missing = []
        values = {'__missing__': missing}
        mrs = []
        for field in fields:
            name = field.get('name')
            selector = field.get('selector')
            sel_type = field.get('sel_type', 'css')
            required = field.get('required', False)
            children = field.get('children')
            process_value = field.get('process_value')
            val = no_default

            if not name and (not children or len(fields) > 1):
                raise Exception(u'必需指定字段名称')

            if sel_type == 'xpath':
                sels = selobj.xpath(selector)
            elif sel_type == 'css':
                sels = selobj.css(selector)
            else:
                continue

            if children:
                cvals = []
                for s in sels:
                    val, mis, mr = self._extract_items(children, s)
                    cvals.append(val)
                    if mis:
                        missing.append(mis)
                    mrs.append(mr)
                val = cvals
            else:

                if isinstance(sels, (Selector, SelectorList)):
                    val = sels.text()

            if val is not no_default and val is not None:
                if process_value:
                    if isinstance(process_value, six.string_types):
                        process_value = get_function(process_value, 'process_value', field=field)
                    val = process_value(val, field, values)
                if isinstance(val, six.string_types):
                    val = val.strip()
                if not name and children and len(fields) == 1:
                    values = val
                else:
                    values[name] = val
            elif required:
                missing.append(name)
        if mrs:
            mr = sum(mrs) * 1.0 / len(mrs)
        else:
            mr = len(missing) * 1.0 / len(fields)
        if isinstance(values, dict):
            ms = values.get('__missing__')
            if not ms:
                del values['__missing__']
        ir = ItemResult(data=values, miss_fields=missing, miss_rate=mr)
        return ir

    def extract_links(self, rules, selector=None, **kw):
        # print('--extract_links => ', rules)
        if isinstance(rules, six.string_types) and selector:
            return self._extract_links(rules, selector=selector, **kw)

        if isinstance(rules, dict):
            page = rules.pop('page')
            return self._extract_links(page, **rules)

        all_links = []
        for rule in rules:
            page = rule.pop('page')
            links = self._extract_links(page, **rule)
            all_links.extend(links)
        return all_links

    def _extract_links(self, page, **kw):
        selobj = self.sel
        links = set()
        selector = kw.pop('selector')
        sel_type = kw.pop('sel_type', 'css')
        if sel_type == 'xpath':
            els = selobj.xpath(selector)
        else:
            els = selobj.css(selector)
        # print els, selector, sel_type
        attr = kw.pop('attr', 'href')
        allows = kw.pop('allows', None)
        denies = kw.pop('denies', None)
        process_value = kw.pop('process_value', None)
        if process_value:
            if isinstance(process_value, six.string_types):
                process_value = get_function(process_value, 'process_value')

        allow_res = [x if isinstance(x, _re_type) else re.compile(x) for x in arg_to_iter(allows)] if allows else None
        deny_res = [x if isinstance(x, _re_type) else re.compile(x) for x in arg_to_iter(denies)] if denies else None

        for el in els:
            if isinstance(el, Selector):
                href = el.attr(attr)
                text = el.text()
            else:
                href, text = el, ''
            if href is None and text:
                href, text = text, href

            if process_value:
                href, text = process_value(href, text)

            if href and is_valid_url(href):
                href = href.strip()
                if allow_res and not _matches(href, allow_res):
                    continue
                if deny_res and _matches(href, deny_res):
                    continue
                conf = kw.copy()
                conf['text'] = text
                conf['df_enable'] = kw.get('df_enable', True)
                link = Link(page, href, **conf)
                links.add(link)
        return list(links)

