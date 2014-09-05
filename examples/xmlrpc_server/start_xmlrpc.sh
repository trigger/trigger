#!/bin/bash

# Kill existing twistd
killall twistd

# Start the mofo
TWISTD=`which twistd`
#$TWISTD -l trigger-xmlrpc.log --pidfile /var/run/trigger-xmlrpc.pid trigger-xmlrpc
$TWISTD -l trigger-xmlrpc.log trigger-xmlrpc -p 9000 -s 9001

# Watch the log
tail -f trigger-xmlrpc.log
