
import json
from collections import defaultdict
from flask import request, jsonify
from flask_admin.base import BaseView, expose
from flask_admin.form import BaseForm, FormOpts, rules
from yunduo.resource import get_connection
from xadmin.helpers import current_project
from xadmin.view.base import BaseMixin


class StatView(BaseMixin, BaseView):

    can_create = False
    can_edit = False
    can_delete = False

    def __init__(self, *args, **kwargs):
        super(StatView, self).__init__(*args, **kwargs)
        self.influx_stat = get_connection('stat')

    @expose('/')
    def index_view(self):

        template = "/admin/model/stat_index.html"
        return self.render(template)

    def parse_state(self):
        field = 'COUNT(/p_1\d/), COUNT(p_20), COUNT(p_21)'

        f1 = 'COUNT(/f_\d+/)'

        f2 = ('COUNT(/p_1\d/), COUNT(p_20) AS count_p_20, COUNT(p_21) AS count_p_20,'
              'COUNT(p_30) AS count_p_20, COUNT(p_31) AS count_p_20')

        f3 = 'SUM(p_22) AS sum_p_22, SUM(p_23) AS sum_p_23, SUM(p_32) AS sum_p_32, SUM(p_33) AS sum_p_33'

    def download_stat(self):
        field = 'COUNT(/f_\d+/)'


    @expose('/stat/')
    def get_stat(self):
        args = request.args
        where = ["project=$project"]
        params = {"project": current_project.alias}  # 'project',
        for key in ('job', 'page', 'action', 'batch_id'):
            val = args.get(key)
            if val:
                where.append("%s=$%s" % (key, key))
                params[key] = val

        start = args.get('start')
        if start:
            where.append("time>=$start_time")
            params['start_time'] = start

        end = args.get('end')
        if end:
            where.append("time<$end_time")
            params['end_time'] = end

        time_interval = args.get('interval', '1h')
        groupby = ' GROUP BY time(%s)' % time_interval if time_interval else ''
        where = ' WHERE %s' % ' AND '.join(where) if where else ''
        sqls = []
        flds = ('COUNT(/f_\d+/)',
                ('COUNT(/p_1\d/), COUNT(p_20) AS count_p_20, COUNT(p_21) AS count_p_21,'
                 'COUNT(p_30) AS count_p_30, COUNT(p_31) AS count_p_31'),
                'SUM(p_22) AS sum_p_22, SUM(p_23) AS sum_p_23, SUM(p_32) AS sum_p_32, SUM(p_33) AS sum_p_33')
        for fld in flds:
            sqls.append("SELECT %s FROM crawl_stat%s%s" % (fld, where, groupby))

        sql = ';'.join(sqls)
        # print(sql, params)
        rs = self.influx_stat.query(sql, params={'params': json.dumps(params)})
        # data = [list(r.get_points()) for r in rs]
        data = defaultdict(list)
        timedata = []
        first = True
        for r in rs:
            for points in r.get_points():
                t = points.pop('time')
                if first:
                    timedata.append(t)
                for p in points:
                    data[p].append(points[p])
            first = False

        name_map = {
            'p_10': '被反爬',
            'p_11': '下载重试',
            'p_12': '需解析',
            'p_14': '下载无效',
            'p_20': '内容抽取异常',
            'p_21': '未抽取到内容',
            'p_22': '抽取到内容数',
            'p_23': '保存成功数',
            'p_30': '链接抽取异常',
            'p_31': '未抽取到链接',
            'p_32': '抽取到链接数',
            'p_33': '去重后链接数',
        }

        series = []
        data = dict(data)
        for key in data.keys():
            val = data[key]
            if key.startswith('count_f_'):
                idx = 0
                if key == 'count_f_0':
                    name = '下载异常'
                else:
                    name = 'HTTP %s' % key.replace('count_f_', '')
            elif key.startswith('count_p_'):
                idx = 1
                name = name_map.get(key[6:])
            elif key.startswith('sum_p_'):
                idx = 2
                name = name_map.get(key[4:])
            else:
                continue

            sval = set(val)
            if len(sval) == 1 and sval.pop() is None:
                continue
            val = list(map(lambda i: 0 if i is None else i, val))
            series.append({
                'name': name,
                'type': 'line',
                'xAxisIndex': idx,
                'yAxisIndex': idx,
                'symbolSize': 8,
                'hoverAnimation': False,
                'data': val
            })

        # data['time'] = timedata
        return jsonify({
            'timeData': timedata,
            'series': series
        })




'''
interval: 30s, 5m, 30m, 1h, 12h, 1d  
f_*

总体的：各page，worker的情况
下载的：各code的统计
解析的：链接数，记录数
'''