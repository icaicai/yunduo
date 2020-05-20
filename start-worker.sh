#!/bin/sh

export PYTHONPATH=/home/cai/yunduo/lib:/home/cai/yunduo/app
celery -A xspider.app worker -c 4 -l info -f ./logs/xspider.log
