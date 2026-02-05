#!/usr/bin/env python3

"""Uses Trigger libraries to load configs on network devices.

Please see `~trigger.contrib.docommand.ConfigLoader` for details
"""

from trigger.contrib import docommand


def main():
    """Main entry point for the CLI tool."""
    docommand.main(action_class=docommand.ConfigLoader)


if __name__ == "__main__":
    main()
