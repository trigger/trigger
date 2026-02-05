#!/usr/bin/env python3

"""Uses Trigger libraries to run commands on network devices.

Please see `~trigger.contrib.docommand.CommandRunner` for details.
"""

from trigger.contrib import docommand


def main():
    """Main entry point for the CLI tool."""
    docommand.main(action_class=docommand.CommandRunner)


if __name__ == "__main__":
    main()
