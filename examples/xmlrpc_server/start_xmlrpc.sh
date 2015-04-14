#!/bin/bash

# Kill existing twistd
if [ -e twistd.pid ]; then
    kill `cat twistd.pid`
    echo "Killed twistd"
fi

# Start the mofo
TWISTD=`which twistd`
#$TWISTD -l trigger-xmlrpc.log --pidfile /var/run/trigger-xmlrpc.pid trigger-xmlrpc
$TWISTD -l trigger-xmlrpc.log trigger-xmlrpc -p 9090 -s 9091

# Start the mofo
TWISTD=`which twistd`
#$TWISTD -l trigger-xmlrpc.log --pidfile /var/run/trigger-xmlrpc.pid trigger-xmlrpc
$TWISTD -l trigger-xmlrpc.log trigger-xmlrpc -p 9000 -s 9001

# Watch the log
tail -f trigger-xmlrpc.log
