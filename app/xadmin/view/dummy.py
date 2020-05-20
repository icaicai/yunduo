
import random
from flask import request
from flask_admin.base import BaseView, expose


class DummyView(BaseView):

    can_create = False
    can_edit = False
    can_delete = False

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('endpoint', 'endpoint_%s' % (random.random() * 100))
        super(DummyView, self).__init__(*args, **kwargs)

    @expose('/')
    def index_view(self):

        template = "/admin/model/dummy.html"
        return self.render(template)


