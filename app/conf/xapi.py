
class Config(object):
    DEBUG = True
    TESTING = False
    MONGODB_SETTINGS = {
        'db': 'xspider',
        'host': '127.0.0.1'
    }
    MULTIPART_FORM_FIELDS_AS_JSON = True
    AUTO_COLLAPSE_MULTI_KEYS = True

