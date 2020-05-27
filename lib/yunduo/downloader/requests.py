
# import random
from requests import Session
# from mergedict import ConfigDict
# from conf.common import HTTP_DEFAULT_HEADERS, HTTP_TIMEOUT
from .models import Request, Response
# from .phantomjs import phantomjs_download, Phantomjs
# from proxy import get_proxy, report_proxy


# method=None, url=None, headers=None, files=None,
# data=None, params=None, auth=None, cookies=None, hooks=None, json=None


def requests_download(preq, **kwargs):
    sess = Session()
    resp = sess.send(preq, **kwargs)
    resp.cookies = sess.cookies
    return Response.from_response(resp)

