# coding=utf8

from flask import Flask, url_for
from flask_login import user_logged_in
import flask_admin
from flask_babelex import Babel
from xadmin.model import db, Project, Script, Page, Job
# from xadmin.model.accredit import Accredit
from xadmin.model.form import Form
from xadmin.model.action import Action
from xadmin.model.alert import Alert

from xadmin.view import (MyAdminIndexView, DummyView, ProjectView, JobView, PageView, ActionView,
                         ScriptView, LogView, AlertView, FormView, StatView)

from xadmin.base import user
from xadmin.helpers import current_project, set_current_project
from xadmin.celeryevents import celery_events

app = Flask('xadmin')
app.config.from_object('conf.xadmin.Config')
# h = BufferedMongoHandler(capped=True, collection='tasks')
# app.logger.addHandler(h)

# flask_wtf.CSRFProtect(app)
babel = Babel(app)
db.init_app(app)
# user.security.init_app(app, user.user_datastore)

# Flask views
# @app.route('/')
# def index():
#     return '<a href="/admin/">Click me to get to Admin!</a>'

@app.context_processor
def inject_project():
    return dict(current_project=current_project)


def init_current_project(*args, **kw):
    print('before_first_request init_current_project ==> ', current_project, current_project is None)
    if not current_project:
        project = Project.objects().first()
        print('get first project', project)
        set_current_project(project)

user_logged_in.connect(init_current_project, app)


# Create admin
admin = flask_admin.Admin(app, u'管理平台', index_view=MyAdminIndexView(), template_mode='bootstrap3')
user.init_app(app, admin)

# Add views
admin.add_view(ProjectView(Project, u'项目', category=u"项目管理"))
admin.add_view(JobView(Job, u'任务', category=u"项目管理", menu_icon_type='fa', menu_icon_value='fa-dashboard'))
admin.add_view(PageView(Page, u'页面', category=u"项目管理", menu_icon_type='fa', menu_icon_value='fa-dashboard'))
admin.add_view(FormView(Form, u'表单', category=u"项目管理"))
admin.add_view(ActionView(Action, u'动作', category=u"项目管理"))
admin.add_view(ScriptView(Script, u'脚本', category=u"项目管理"))
# admin.add_view(DummyView(u'反爬', category=u"项目管理"))
admin.add_view(AlertView(Alert, u'监控', category=u"项目管理"))
admin.add_view(StatView(u'报表', category=u"项目管理"))
admin.add_view(LogView(u'日志', category=u"项目管理"))

# admin.add_view(EMailHostView(EMailHost, u'邮箱设置', category=u"邮箱账单"))
# admin.add_view(EMailBillView(EMailBill, u'账单解析', category=u"邮箱账单"))
# admin.add_view(AccreditView(Accredit, u'登录元素', category=u"授权管理"))
# admin.add_view(AccreditView(Accredit, u'登录设置', category=u"授权管理"))
# admin.add_view(DummyView(u'监控', category=u"授权管理"))
# admin.add_view(DummyView(u'报告', category=u"授权管理"))
# admin.add_view(DummyView(u'日志', category=u"授权管理"))

admin.add_view(DummyView(u'系统设置', category=u"系统管理"))
admin.add_view(DummyView(u'Worker', category=u"系统管理"))
admin.add_view(DummyView(u'任务调度', category=u"系统管理"))
# admin.add_view(DummyView(u'日志', category=u"系统设置"))

# admin.add_view(StatView(u'数据统计'))

# admin.add_view(LogView('crawl', u'抓取日志', endpoint='clog', category=u"任务日志"))
# admin.add_view(LogView('authorized', u'授权日志', endpoint='alog', category=u"任务日志"))
# admin.add_view(TaskView('crawl', u'抓取任务信息', endpoint='ctask', category=u"任务日志"))
# admin.add_view(TaskView('authorized', u'授权任务信息', endpoint='atask', category=u"任务日志"))
# m = admin.get_category_menu_item(u"用户管理")
# m.icon_type = 'fa'
# m.icon_value = 'fa-dashboard'

m = admin.get_category_menu_item(u"项目管理")
m.icon_type = 'fa'
m.icon_value = 'fa-dashboard'




# @user.security.context_processor
# def security_context_processor():
#     return dict(
#         admin_base_template=admin.base_template,
#         admin_view=admin.index_view,
#         h=flask_admin.helpers,
#         get_url=url_for
#     )

celery_events(app)

