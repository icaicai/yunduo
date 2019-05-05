# coding=utf8

from yunduo.queue import get_job_queue, get_action_queue


enable_utc = True
timezone = 'Asia/Shanghai'
result_backend = 'redis://127.0.0.1/1'
result_expires = 3600
result_serializer = 'pickle'

accept_content = ['pickle']


# beat_scheduler = ''
# task_reject_on_worker_lost

task_queues = {
    'xspider': {
        'exchange': 'xspider',
        'routing_key': 'xspider',
    },
    'xcrawl': {
        'exchange': 'xcrawl',
        'queue_arguments': {
            'x-max-priority': 10
        },
        'consumer_arguments': {
            'x-priority': 8
        }
    },
    'xaction': {
        'exchange': 'xaction',
        'routing_key': 'xaction',
        'consumer_arguments': {
            'x-priority': 9
        }
    },
    'xsave': {
        'exchange': 'xsave',
        'routing_key': 'xsave',
        'consumer_arguments': {
            'x-priority': 10
        }
    },
    'xlog': {
        'exchange': 'xlog',
        'routing_key': 'xlog',
        'consumer_arguments': {
            'x-priority': 6
        }
    }
}


def route_for_crawl(task, args, kwargs, options, task_type):
    if task == 'xspider.crawl':
        batch_id = kwargs.get('batch_id', 'default')
        q = get_job_queue(args[0], args[1], batch_id)
        return {'queue': q}
    elif task == 'xspider.action':
        q = get_action_queue(args[0], args[1])
        return {'queue': q}

    return None


task_routes = [route_for_crawl, {
    # 'xspider.crawl': {
    #     'queue': 'xcrawl',
    # },
    # 'xspider.action': {
    #     'queue': 'xaction',
    # },
    'xspider.save_log': {
        'queue': 'xlog',
    },
    'xspider.run_script': {
        'queue': 'xspider',
    },
    'xspider.monitor': {
        'queue': 'xspider',
    },
    'xspider.clear_script': {
        'queue': 'xspider',
    }
}]

task_protocol = 2
task_serializer = 'pickle'
task_compression = 'gzip'

task_default_queue = 'xspider'
task_default_exchange = 'xspider'
task_default_exchange_type = 'direct'
task_default_routing_key = 'xspider'
task_create_missing_queues = True

worker_max_tasks_per_child = 1000
worker_log_format = '%(asctime)s %(levelname)s/%(processName)s %(message)s'
worker_task_log_format = '%(asctime)s %(levelname)s/%(processName)s %(task_name)s/%(task_id)s %(task_info)s %(message)s'
                       # "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"
worker_redirect_stdouts_level = 'INFO'
# worker_max_tasks_per_child = 1000

# broker_url = 'amqp://celery:celery@192.168.56.101'  # celery  passwdcelery
# broker_url = 'amqp://celery:celerypasswd@127.0.0.1:5672/yunduo'
broker_url = 'amqp://celery:passwdcelery@127.0.0.1:5672/yunduo'


# beat_schedule
beat_scheduler = 'xbeat:Scheduler'
beat_max_loop_interval = 60
# beat_redis_url = 'redis://127.0.0.1/3'
beat_key_prefix = 'beat:'
# beat_lock_ttl = 300

# CELERY_REDIS_SCHEDULER_URL = "redis://127.0.0.1/3"
# CELERY_REDIS_SCHEDULER_KEY_PREFIX = 'tasks:meta:'


# download
# spi_headers = [{
#     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
#     'Accept-Encoding': 'deflate',
#     'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
# }]


# spi_timeout = 3
# spi_max_retries = 3
# spi_retry_code = [401, 407, 500, 503, 507]

# spi_proxy_service = 'http://localhost/'

# save
# default_db_type = 'mongo'
# default_db_host = 'localhost'
# default_db_name = 'pages'
# default_db_table = 'pages'




