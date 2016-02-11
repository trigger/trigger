#coding=utf-8

"""
Templating functions for unstructured CLI output.
"""

__author__ = 'Thomas Cuthbert'
__maintainer__ = 'Thomas Cuthbert'
__email__ = 'tcuthbert90@gmail.com'
__copyright__ = 'Copyright 2016 Trigger Org'


import sys
import os
from trigger.conf import settings

try:
    import textfsm
except ImportError:
    print("""
    Woops, looks like you're missing the textfsm library.

    Try installing it like this::

        >>> pip install gtextfsm
    """)


# Exports
__all__ = ('load_cmd_template', )


def _template_path(dev_type, cmd):
    """
    Return textfsm templates from the directory pointed to by the TEXTFSM_TEMPLATE_DIR trigger variable.

    :param dev_type: Type of device ie cisco_ios, arista_eos
    :type  dev_type: str
    :param cmd: CLI command to load template.
    :type  cmd: str
    :returns: String template path
    """
    t_dir = settings.TEXTFSM_TEMPLATE_DIR
    return '{0}/{1}_{2}.template'.format(t_dir, dev_type, cmd.replace(' ', '_'))


def load_cmd_template(dev_type, cmd):
    """
    :param dev_type: Type of device ie cisco_ios, arista_eos
    :type  dev_type: str
    :param cmd: CLI command to load template.
    :type  cmd: str
    :returns: String template path
    """
    if dev_type.lower() == u'cisco':
        with open(_template_path("cisco_ios", cmd), 'rb') as f:
            return textfsm.TextFSM(f)


def get_textfsm_object(re_table, cli_output):
    "Returns structure object from TextFSM data."
    from collections import defaultdict
    rv = defaultdict(list)
    keys = re_table.header
    values = re_table.ParseText(cli_output)
    l = []
    for item in values:
        l.extend(zip(keys, item))

    for k, v in l:
        rv[k].append(v)

    return dict(rv)
