#!/bin/sh

num=`ps wx | grep 'celery worker' | grep -v grep | wc -l`
while [ $num -gt 0 ]
do
  echo "Kill $num"
  ps wx | grep 'celery worker' | grep -v grep | awk '{print $1}' | xargs kill
  sleep 1
  num=`ps wx | grep 'celery worker' | grep -v grep | wc -l`
done
echo "DONE"
