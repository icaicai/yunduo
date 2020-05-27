#!/bin/sh
DIR=$(cd `dirname $0`; pwd)
export PYTHONPATH=$DIR/lib:$DIR/app
celery -A xspider.app beat -l info -f ./logs/yunduo-beat.log
