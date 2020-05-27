#!/bin/sh
DIR=$(cd `dirname $0`; pwd)
export PYTHONPATH=$DIR/lib:$DIR/app
celery -A xspider.app worker -c 4 -l info -f ./logs/xspider.log
