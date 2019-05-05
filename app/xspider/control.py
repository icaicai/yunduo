
import sys
from celery.app import control
from celery.five import text_t
from celery.worker.control import control_command


class Control(control.Control):

    def clear_script(self, project, script, destination=None, **kwargs):
        return self.broadcast(
            'clear_script',
            arguments={
                'project': project,
                'script': script
            },
            destination=destination,
            **kwargs)


@control_command(
    args=[('project', text_t), ('script', text_t)],
    signature='<project> <script>',
)
def clear_script(state, project, script, **kwargs):
    try:
        scripts = sys.modules['__scripts__']
        name = '%s_%s' % (project if project else '', script)
        if hasattr(scripts, name):
            delattr(scripts, name)
    except Exception:
        import traceback
        traceback.print_exc()
