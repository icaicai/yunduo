#!/bin/sh

num=`ps wx | grep 'bin/flask run' | grep '8181' | grep -v grep | wc -l`
while [ $num -gt 0 ]
do
  echo "Kill $num"
  ps wx | grep 'bin/flask run' | grep -v grep | awk '{print $1}' | xargs kill
  sleep 1
  num=`ps wx | grep 'bin/flask run' | grep '8181' | grep -v grep | wc -l`
done
echo "DONE"
