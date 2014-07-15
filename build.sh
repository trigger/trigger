#!/bin/bash
## This script uninstalls a currently installed trigger installation, and
## installs the version of trigger in this directory (by using the provided
## setup.py script).

if [ $(whoami) != "root" ]
then
    echo "ERROR: script must be run as root. Try 'sudo build.sh'"
    exit 1
fi

echo "Uninstalling trigger..."
pip uninstall trigger

if [ $? != 0 ]
then
    echo "ERROR: uninstallation of python failed. Quitting..."
    exit 1
fi

echo "Installing trigger from source..."
python setup.py install

if [ $? != 0 ] 
then
    echo "ERROR: installation of python failed. Quitting..."
    exit 1
fi
