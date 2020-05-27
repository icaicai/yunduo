
import requests
# from conf.common import HTTP_PROXY_SERVICE
from yunduo.conf import xconf

HTTP_PROXY_SERVICE = xconf.get_http('proxy_service')
_get_url = '%sget' % HTTP_PROXY_SERVICE
_report_url = '%sreport' % HTTP_PROXY_SERVICE


def get_proxy(type_):
    try:
        r = requests.get(_get_url, headers={'Connection': 'keep-alive'}, timeout=2)
        if r and r.text:
            return {"http": r.text, "https": r.text}
    except Exception:
        pass


def feedback_proxy(proxy, status):
    try:
        r = requests.get(_report_url,
                         params={'proxy': proxy['http'], 'status': status},
                         headers={'Connection': 'keep-alive'},
                         timeout=2)
        if r:
            return r.text
    except Exception:
        pass
