

connection = {
    'conf': {
        'dsn': 'redis://192.168.56.101/2'
    },
    'df': {
        'dsn': 'redis://192.168.56.101/3',
    },
    'run': {
        'dsn': 'redis://192.168.56.101/4'
    },
    'page': {
        'dsn': 'mongodb://192.168.56.101/',
        'db': 'yunduo_pages'
    },
    'task': {
        'dsn': 'mongodb://192.168.56.101/',
        'db': 'yunduo_tasks'
    },
    'log': {
        'dsn': 'mongodb://192.168.56.101/',
        'db': 'yunduo_logs'
    },
    'result': {
        'dsn': 'mongodb://192.168.56.101/',
        'db': 'yunduo_results'
    },
    'stat': {
        'dsn': 'influxdb://192.168.56.101:8086/yunduo_stat'
    }
}


rabbitmq_monitor_uri = ''


# download
http = {
    'timeout': 3,
    'max_retries': 3,
    'retry_codes': [401, 407, 500, 503, 574],
    'headers': {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                       ' Chrome/65.0.3325.162 Safari/537.36'),
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    },
    'proxy_service': 'http://localhost:9088/'
}


