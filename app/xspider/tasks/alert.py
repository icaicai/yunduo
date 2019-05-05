# coding=utf8

import time
import json
from yunduo.resource import get_connection
from xspider.jobaction import JobAction
from xspider.app import app
from .base import BaseTask


class AlertTask(BaseTask):
    # Strategy = 'xspider.strategy:default'

    def initialize(self):
        self.redis_run = get_connection('run')
        self.influx_stat = get_connection('stat')

    def send_mail(self):
        pass



@app.task(bind=True, base=AlertTask, name='xspider.alert')
def alert(self, project, job, rules, **kwargs):
    # ja = JobAction(project, job)
    if not self.redis_run.hexists('project:running', project):
        return

    where = ["project=$project"]
    params = {"project": project}  # 'project',
    if job:
        where.append("job=$job")
        params["job"] = job

    for key in ('page', 'action', 'batch_id'):
        val = kwargs.get(key)
        if val:
            where.append("%s=$%s" % (key, key))
            params[key] = val

    interval = rules['time_range']
    now = time.time()
    start = now - interval

    where.append("time>=$start_time")
    params['start_time'] = start

    where.append("time<$end_time")
    params['end_time'] = now

    time_interval = '%ds' % (interval / 10)
    groupby = ' GROUP BY time(%s)' % time_interval if time_interval else ''
    where = ' WHERE %s' % ' AND '.join(where) if where else ''
    sqls = []
    # flds = ('COUNT(/f_\d+/)',
    #         ('COUNT(/p_1\d/), COUNT(p_20) AS count_p_20, COUNT(p_21) AS count_p_21,'
    #          'COUNT(p_30) AS count_p_30, COUNT(p_31) AS count_p_31'),
    #         'SUM(p_22) AS sum_p_22, SUM(p_23) AS sum_p_23, SUM(p_32) AS sum_p_32, SUM(p_33) AS sum_p_33')
    # for fld in flds:
    #     sqls.append("SELECT %s FROM crawl_stat%s%s" % (fld, where, groupby))
    fld = rules['field']
    sqls.append("SELECT %s FROM crawl_stat%s%s" % (fld, where, groupby))

    sql = ';'.join(sqls)
    # print(sql, params)
    rs = self.influx_stat.query(sql, params={'params': json.dumps(params)})
    data = [list(r.get_points()) for r in rs]


    for rule in rules:
        self.influx_stat
        # rs = self.influx_stat.query(sql, params={'params': json.dumps(params)})

