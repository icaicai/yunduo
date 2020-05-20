
import requests
from flask import current_app

base_uri = 'http://celery:passwdcelery@localhost:15672/api/queues'


def get_queues(porject, is_auth=False):
    if is_auth:
        queues_uri = base_uri
    else:
        queues_uri = '{0}/%2F/proj_{1}'.format(base_uri, porject)

    print queues_uri
    resp = requests.get(queues_uri)
    if resp.status_code == 200:
        queues = resp.json()
        if not is_auth:
            return [queues]

        proj = 'proj_{}:'.format(porject)
        qs = []
        for q in queues:
            name = q['name']
            if name.startswith(proj):
                qs.append(q)

        return qs

