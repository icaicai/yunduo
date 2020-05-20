# coding=utf8

from flask import Flask, url_for, redirect, render_template, request
from flask_security import (Security, MongoEngineUserDatastore, UserMixin, RoleMixin)
from flask_admin import helpers as admin_helpers
from xadmin.model import db


class Role(db.Document, RoleMixin):
    name = db.StringField(max_length=80, unique=True)
    description = db.StringField(max_length=255)


class User(db.Document, UserMixin):
    name = db.StringField(max_length=255, unique=True)
    email = db.StringField(max_length=255, unique=True)
    password = db.StringField(max_length=255)
    active = db.BooleanField(default=True)
    confirmed_at = db.DateTimeField()
    roles = db.ListField(db.ReferenceField(Role), default=[])

    def __str__(self):
        return '%s < %s >' % (self.name, self.email)


# Setup Flask-Security
user_datastore = MongoEngineUserDatastore(db, User, Role)
security = Security()


def init_app(app, admin):
    security._state = security.init_app(app, user_datastore)

    @security.context_processor
    def security_context_processor():
        return dict(
            admin_base_template='admin/base.html',
            # admin_view=admin.index_view,
            h=admin_helpers,
            get_url=url_for
        )

