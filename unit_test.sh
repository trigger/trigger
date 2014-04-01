#!/bin/sh

########################################
#
# Author : Autumn Wang
# Date   : 03/26/2014
#
# This is the wrapper shell script to 
# run unit test.
#
#########################################

BASEDIR=$(dirname $0)

export PATH=/opt/bin:${PATH}
export TACACSRC_KEYFILE=${BASEDIR}/tests/data/tackf
export TACACSRC=${BASEDIR}/tests/data/tacacsrc

python2.7 -W ignore::RuntimeWarning ${BASEDIR}/setup.py test
