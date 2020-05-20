#!/bin/sh
export PYTHONPATH=/home/cai/yunduo/lib:/home/cai/yunduo/app
export FLASK_DEBUG=1
export FLASK_APP=xadmin.app
flask run -h 0.0.0.0 -p 8181 --with-threads

