# coding=utf8

from kombu.entity import Exchange, Queue


def get_job_queue(project, job, batch_id):
    binding_key = batch_id
    name = 'xcrawl:%s:%s:%s' % (project, job, binding_key)
    return Queue.from_dict(name,
                           binding_key=binding_key,
                           exchange='xcrawl',
                           exchange_type='direct',
                           queue_arguments={'x-max-priority': 10},
                           consumer_arguments={'x-priority': 8})


def get_action_queue(project, action):
    binding_key = '%s:%s' % (project, action)
    name = 'xaction:%s:%s' % (project, action)
    return Queue.from_dict(name,
                           binding_key=binding_key,
                           exchange='xaction',
                           exchange_type='direct',
                           queue_arguments={'x-max-priority': 10},
                           consumer_arguments={'x-priority': 9})