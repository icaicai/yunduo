
class Config(object):
    DEBUG = True
    TESTING = False
    SECRET_KEY = '123343454657678uhg'
    SECURITY_PASSWORD_SALT = '098765432qsfhy'
    # SECURITY_USER_IDENTITY_ATTRIBUTES = ['name']
    SECURITY_LOGIN_USER_TEMPLATE = 'admin/login.html'
    CSRF_ENABLED = True
    MONGODB_SETTINGS = {
        'db': 'yunduo',
        'host': '192.168.56.101'
    }
    BABEL_DEFAULT_LOCALE = 'zh_CN'
    BABEL_DEFAULT_TIMEZONE = 'Asia/Shanghai'

