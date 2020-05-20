#!/bin/sh

export PYTHONPATH=/home/cai/yunduo/lib:/home/cai/yunduo/app
celery -A xspider.app beat -l info -f ./logs/yunduo-beat.log
