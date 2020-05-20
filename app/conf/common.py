# @TODO
# DELETE THIS FILE

# Redis
rediss = {
    'conf': 'redis://127.0.0.1/2',
    'df': 'redis://127.0.0.1/3',
    'run': 'redis://127.0.0.1/4'
}

mongos = {
    'page': 'mongodb://127.0.0.1/',
    'log': 'mongodb://127.0.0.1/',
    'result': 'mongodb://127.0.0.1/',
}

influx_stat = 'influxdb://127.0.0.1:8086/spider_state'

# download
HTTP_DEFAULT_HEADERS = [{
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
}]


HTTP_TIMEOUT = 3
HTTP_MAX_RETRIES = 3
HTTP_RETRY_CODE = [401, 407, 500, 503, 574]
HTTP_PROXY_SERVICE = 'http://localhost:8088/'
