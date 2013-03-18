#!/bin/bash

# Start the mofo
TWISTD=`which twistd`
$TWISTD -l trigger-xmlrpc.log --pidfile /var/run/trigger-xmlrpc.pid trigger-xmlrpc

# Kill existing twistd
killall twistd

# Watch the log
tail -f trigger-xmlrpc.log
