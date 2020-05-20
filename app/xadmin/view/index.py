# coding=utf8

from flask import url_for, redirect, request, abort
from flask_security import current_user
import flask_admin


class MyAdminIndexView(flask_admin.AdminIndexView):

    def __init__(self, *args, **kwargs):
        kwargs['url'] = '/'
        super(MyAdminIndexView, self).__init__(*args, **kwargs)
        # self.endpoint = self._get_endpoint('/')

    def is_accessible(self):
        return current_user.is_authenticated

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))

    @flask_admin.expose('/')
    def index(self):
        # if not current_user.is_authenticated:
        #     return redirect(url_for('security.login', next=request.url))
            # return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()
