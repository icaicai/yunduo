# coding=utf8

from wtforms import widgets
from flask_mongoengine.wtf import fields


class HiddenModelSelectField(fields.ModelSelectField):

    widget = widgets.HiddenInput()
