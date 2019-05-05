
from __future__ import absolute_import
# from gevent import monkey
# monkey.patch_all()
# import logging
# from conf import constants
from yunduo.conf import xconf
from xspider import log

log.setup_logger()
xconf.from_object('conf.base')

#from .app import app
