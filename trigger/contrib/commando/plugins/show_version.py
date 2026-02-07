"""Commando plugin for retrieving version information from network devices."""

from typing import ClassVar

from twisted.python import log

from trigger.contrib.commando import CommandoApplication

task_name = "show_version"


def xmlrpc_show_version(*args, **kwargs):
    """Run 'show version' on the specified list of `devices`."""
    log.msg("Creating ShowVersion")
    sc = ShowVersion(*args, **kwargs)
    return sc.run()


class ShowVersion(CommandoApplication):
    """Simple example to run ``show version`` on devices."""

    commands: ClassVar[list[str]] = ["show version"]
