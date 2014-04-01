#!/bin/sh

########################################
#
# Author : Autumn Wang
# Date   : 03/26/2014
#
# This is the wrapper shell script to 
# run acceptance test.
#
#########################################

#Test whether HOME variable is set and set to /tmp if not
if [ -z "$HOME" ]
then
  export HOME=/tmp
fi

BASEDIR=$(dirname $0)

export PATH=/opt/bin:${PATH}
export TRIGGER_TEST_DIR=${BASEDIR}/tests/acceptance
export TRIGGER_SETTINGS=${TRIGGER_TEST_DIR}/data/settings.py
export NETDEVICES_SOURCE=${TRIGGER_TEST_DIR}/data/netdevices.xml
export BOUNCE_FILE=${TRIGGER_TEST_DIR}/data/bounce.py

python2.7 -W ignore::RuntimeWarning ${BASEDIR}/tests/acceptance/trigger_acceptance_tests.py
