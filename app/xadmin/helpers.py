# coding=utf8

from werkzeug.local import LocalProxy
from flask import (_request_ctx_stack, session, has_request_context)


current_project = LocalProxy(lambda: _get_project())


def _get_project():
    if has_request_context() and not hasattr(_request_ctx_stack.top, 'project'):
        from xadmin.model.project import Project

        ctx = _request_ctx_stack.top
        project_id = session.get('project_id')
        if project_id is None:
            ctx.project = Project.objects().first()
        else:
            project = Project.objects.filter(pk=project_id).first()
            if project is None:
                ctx.project = Project.objects().first()
            else:
                ctx.project = project

    return getattr(_request_ctx_stack.top, 'project', None)


def set_current_project(project):
    if has_request_context():
        session['project_id'] = str(project.id)
        ctx = _request_ctx_stack.top
        ctx.project = project
