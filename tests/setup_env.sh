#!/bin/bash
# Setup environment variables to point to a sandbox 

TEST_ROOT=$(cd `dirname "${BASH_SOURCE[0]}"` && pwd)
TEST_DATA=$TEST_ROOT/data

export TRIGGER_SETTINGS="${TEST_DATA}/settings.py"
