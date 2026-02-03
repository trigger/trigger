==============================================================
Migration Guide: v1.6.0 (Python 2.7) → v2.0.0 (Python 3.10+)
==============================================================

This guide helps you migrate from Trigger v1.6.0 (Python 2.7) to v2.0.0 (Python 3.10+).

.. contents:: Table of Contents
   :local:
   :depth: 2

Why Python 3.10+?
=================

Python 2.7 reached end-of-life on January 1, 2020. Python 3.10+ provides:

- **Security**: Critical security fixes no longer backported to Python 2.7
- **Performance**: Python 3.10+ is significantly faster (10-50% in many workloads)
- **Modern features**: Match statements, better error messages, type hints
- **Dependency support**: Major dependencies (Twisted, cryptography) have dropped Python 2.7

Trigger v2.0.0 targets Python 3.10-3.11. Python 3.12+ support is planned but blocked by SimpleParse compatibility.

Breaking Changes
================

1. Python Version Requirement
------------------------------

**Before (v1.6.0):**

.. code-block:: bash

   python2.7 --version  # Python 2.7.18

**After (v2.0.0):**

.. code-block:: bash

   python --version  # Python 3.10.x or 3.11.x required

2. CLI Tool Entry Points
-------------------------

**Before (v1.6.0):**

CLI tools were located in ``bin/`` directory and invoked directly:

.. code-block:: bash

   ./bin/acl --help
   ./bin/netdev --help

**After (v2.0.0):**

CLI tools are installed as entry points via pip:

.. code-block:: bash

   acl --help
   netdev --help

All 14 CLI tools are now properly packaged:

- ``acl``, ``acl_script``, ``aclconv``
- ``check_access``, ``check_syntax``
- ``fe``, ``find_access``
- ``gnng``, ``gong``
- ``load_acl``, ``load_config``
- ``netdev``, ``optimizer``, ``run_cmds``

3. Test Runner
--------------

**Before (v1.6.0):**

.. code-block:: bash

   ./unit_test.sh
   python setup.py test

**After (v2.0.0):**

.. code-block:: bash

   pytest
   pytest -vv  # verbose mode

4. Build System
---------------

**Before (v1.6.0):**

.. code-block:: bash

   python setup.py install
   python setup.py sdist

**After (v2.0.0):**

.. code-block:: bash

   pip install .
   python -m build  # creates wheel and sdist

The project now uses ``pyproject.toml`` instead of ``setup.py``.

5. Dependency Versions
----------------------

Major dependency updates:

============== ===================== =====================
Package        v1.6.0 (Python 2.7)   v2.0.0 (Python 3.10+)
============== ===================== =====================
Python         2.7                   3.10-3.11
Twisted        15.5.0 - 16.x         ≥22.10.0
cryptography   ≥1.4                  ≥41.0.0
crochet        1.5.0                 ≥2.0.0
pyparsing      ~2.2.0                ≥3.1.0
redis          Any                   ≥5.0.0
textfsm        gtextfsm              textfsm ≥1.1.0
============== ===================== =====================

6. String/Bytes Handling
------------------------

Python 3 distinguishes strings (unicode) from bytes. Most code handles this transparently, but custom integrations may need updates:

.. code-block:: python

   # Python 2 (v1.6.0) - implicit conversion
   output = socket.recv(1024)  # returns str
   if 'Router>' in output:     # works

   # Python 3 (v2.0.0) - explicit encoding
   output = socket.recv(1024)         # returns bytes
   if b'Router>' in output:           # use bytes literal
   # OR
   if 'Router>' in output.decode():   # decode to str

Installation & Upgrade
======================

Prerequisites
-------------

1. **Python 3.10 or 3.11** installed
2. **virtualenv or venv** (recommended)

Check your Python version:

.. code-block:: bash

   python --version
   # or
   python3.10 --version
   python3.11 --version

Upgrade Steps
-------------

1. Backup Current Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If upgrading an existing environment:

.. code-block:: bash

   # Backup current environment
   pip freeze > requirements-v1.6.0.txt

   # Note location of config files
   echo $TRIGGER_SETTINGS
   echo $NETDEVICES_SOURCE

2. Create New Python 3.10/3.11 Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Create virtual environment
   python3.10 -m venv trigger-env
   source trigger-env/bin/activate

   # Verify Python version
   python --version  # Should show 3.10.x or 3.11.x

3. Install Trigger v2.0.0
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Install from PyPI
   pip install trigger>=2.0.0

   # Or install from source
   git clone https://github.com/trigger/trigger.git
   cd trigger
   git checkout v2.0.0
   pip install -e ".[dev]"

4. Verify Installation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check version
   python -c "import trigger; print(trigger.__version__)"

   # Test CLI tools
   acl --help
   netdev --help

   # Test imports
   python -c "
   import trigger
   from trigger.netdevices import NetDevices
   from trigger.acl import parse
   print('Imports successful')
   "

5. Run Tests (Optional)
~~~~~~~~~~~~~~~~~~~~~~~

If you have test data configured:

.. code-block:: bash

   pytest tests/ -v

Configuration Compatibility
===========================

**Good news**: Configuration files are fully compatible between v1.6.0 and v2.0.0.

Configuration Files (No Changes Needed)
----------------------------------------

These files work identically in v2.0.0:

- **settings.py** - Trigger configuration
- **netdevices.xml/json** - Device metadata
- **autoacl.py** - Implicit ACL assignment
- **bounce.py** - Maintenance windows
- **.tacacsrc** - Encrypted credentials
- **TACACSRC_KEYFILE** - TACACS key file

Environment Variables (No Changes Needed)
------------------------------------------

.. code-block:: bash

   export TRIGGER_SETTINGS="/path/to/settings.py"
   export NETDEVICES_SOURCE="/path/to/netdevices.xml"
   export AUTOACL_FILE="/path/to/autoacl.py"
   export BOUNCE_FILE="/path/to/bounce.py"
   export TACACSRC="/path/to/.tacacsrc"
   export TACACSRC_KEYFILE="/path/to/.tackf"

All environment variables work the same way in v2.0.0.

Common Issues & Solutions
=========================

Issue 1: "ImportError: No module named trigger"
------------------------------------------------

**Cause**: Python 2.7 environment active, or Trigger not installed

**Solution**:

.. code-block:: bash

   # Check Python version
   python --version  # Should be 3.10.x or 3.11.x

   # Install Trigger
   pip install trigger

Issue 2: "command not found: acl" (or other CLI tools)
-------------------------------------------------------

**Cause**: CLI tools not in PATH, or installed with ``--user`` flag

**Solution**:

.. code-block:: bash

   # Ensure pip bin directory is in PATH
   which acl

   # If not found, check pip install location
   python -m site --user-base

   # Add to PATH (add to ~/.bashrc or ~/.zshrc)
   export PATH="$HOME/.local/bin:$PATH"

   # Or reinstall without --user
   pip install --force-reinstall trigger

Issue 3: "UnicodeDecodeError" when connecting to devices
---------------------------------------------------------

**Cause**: Device output contains non-UTF-8 bytes

**Solution**:

.. code-block:: python

   # In your code, specify error handling
   output = device.recv(1024).decode('utf-8', errors='replace')

   # Or use latin-1 encoding for raw bytes
   output = device.recv(1024).decode('latin-1')

Issue 4: "Python 3.12 not supported"
-------------------------------------

**Cause**: SimpleParse C extensions don't compile on Python 3.12+

**Solution**:

.. code-block:: bash

   # Use Python 3.10 or 3.11
   python3.11 -m venv trigger-env
   source trigger-env/bin/activate
   pip install trigger

Issue 5: "ModuleNotFoundError: No module named 'gtextfsm'"
-----------------------------------------------------------

**Cause**: Deprecated package name

**Solution**:

.. code-block:: bash

   # Install textfsm (gtextfsm was a fork)
   pip install textfsm

Issue 6: Tests fail with "TRIGGER_SETTINGS not found"
------------------------------------------------------

**Cause**: Test environment variables not set

**Solution**:

.. code-block:: bash

   # Set test environment variables
   export TRIGGER_SETTINGS="tests/data/settings.py"
   export NETDEVICES_SOURCE="tests/data/netdevices.xml"

   # Or use pytest which sets these automatically via conftest.py
   pytest tests/

Issue 7: Twisted import errors
-------------------------------

**Cause**: Old Twisted version incompatible with Python 3.10+

**Solution**:

.. code-block:: bash

   # Upgrade Twisted
   pip install --upgrade twisted

Rollback Instructions
=====================

If you encounter issues and need to rollback to v1.6.0:

1. Recreate Python 2.7 Environment
-----------------------------------

.. code-block:: bash

   # Deactivate current environment
   deactivate

   # Create Python 2.7 environment
   virtualenv -p python2.7 trigger-py27-env
   source trigger-py27-env/bin/activate

2. Install v1.6.0
-----------------

.. code-block:: bash

   # Install from PyPI
   pip install trigger==1.6.0

   # Or from saved requirements
   pip install -r requirements-v1.6.0.txt

3. Restore Configuration
-------------------------

All configuration files work identically, so no changes needed.

Getting Help
============

If you encounter issues not covered in this guide:

- **GitHub Issues**: https://github.com/trigger/trigger/issues
- **Documentation**: http://trigger.readthedocs.io
- **Gitter Chat**: https://gitter.im/trigger/trigger
- **IRC**: ``#trigger`` on Freenode

When reporting issues, include:

- Python version (``python --version``)
- Trigger version (``python -c "import trigger; print(trigger.__version__)")``)
- Full error traceback
- Relevant configuration (sanitized)

Summary Checklist
=================

Use this checklist to verify your migration:

- [ ] Python 3.10 or 3.11 installed and active
- [ ] Trigger v2.0.0 installed (``pip show trigger``)
- [ ] CLI tools work (``acl --help``, ``netdev --help``)
- [ ] Configuration files copied to new environment
- [ ] Environment variables set correctly
- [ ] Can import trigger modules (``python -c "import trigger"``)
- [ ] Can load NetDevices (``python -c "from trigger.netdevices import NetDevices"``)
- [ ] Tests pass (if applicable): ``pytest tests/``
- [ ] Old Python 2.7 environment backed up or documented

Welcome to Trigger v2.0.0!
