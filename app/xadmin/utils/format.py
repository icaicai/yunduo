# coding=utf8
from jinja2 import Markup


def date_format(view, context, model, name):
    if isinstance(model, dict):
        val = model[name]
    else:
        val = getattr(model, name, None)
    if val:
        return val.strftime('%Y-%m-%d %H:%M:%S')
    return '-'


def map_format(maps):
    def _map(view, context, model, name):
        val = getattr(model, name, None)
        return maps.get(val, val)
    return _map


def edit_link_format(view, context, model, name):
    view_args = view._get_list_extra_args()
    return_url = view._get_list_url(view_args)
    return Markup(
        u"<a href='%s'>%s</a>" % (
            view.get_url('.edit_view', id=model.id, url=return_url),
            model.name
        )
    )
