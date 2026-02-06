# What is Trigger?

[![CI](https://github.com/trigger/trigger/workflows/CI/badge.svg)](https://github.com/trigger/trigger/actions/workflows/ci.yml)

Trigger is a robust network automation toolkit written in Python that was
designed for interfacing with network devices and managing network
configuration and security policy. It increases the speed and efficiency of
managing large-scale networks while reducing the risk of human error.

Started by the AOL Network Security team in 2006, Trigger was originally
designed for security policy management on firewalls, routers, and switches. It
has since been expanded to be a full-featured network automation toolkit.

With the high number of network devices on the AOL network this application is
invaluable to performance and reliability. We hope you'll find it useful on
your network and consider participating!

## Supported Platforms

* Cisco IOS, NX-OS, and ASA software
* Juniper Junos and ScreenOS
* Force10 router and switch platforms running FTOS
* Arista Networks 7000-family switches
* ... and more!

Refer to the [official docs](https://trigger.readthedocs.io/en/latest/#supported-platforms) for the full list.

## Key Features

Trigger is designed to work at scale and can support hundreds or thousands of
network devices with ease. Here are some of things that make Trigger tick:

+ Support for SSH, Telnet, and Juniper's Junoscript XML API.
+ Easily get an interactive shell or execute commands asynchronously.
+ Leverage advanced event-driven functionality to manage any number of
  jobs in parallel and handle output or errors as they return.
+ Powerful metadata interface for performing complex queries to group and
  associate network devices by name, manufacturer, type, location, and more.
+ Encrypted storage of login credentials so you can interact without constantly
  being prompted to enter your password.
+ Flexible access-list & firewall policy parser that can test access if access
  is permitted, or easily convert ACLs from one format to another.
+ Detailed support for timezones and maintenance windows.
+ Import your metadata from an existing [RANCID](http://shrubbery.net/rancid/) installation or a CSV file to get up-and-running quickly.
+ A suite of tools for simplifying many common tasks.

## Getting Started

The best way to get started is to read the documentation hosted by [Read the
Docs](http://readthedocs.org) at [https://trigger.readthedocs.io](https://trigger.readthedocs.io). There you will find everything you need to
get going including usage examples, installation and configuration
instructions, and more!

### Python Version Requirements

**Trigger v2.0.0+** requires **Python 3.10 or 3.11**. Python 3.12+ is not yet supported due to SimpleParse C extension compatibility issues.

**Python 2.7 support ended with v1.6.0** (the last Python 2.7 compatible release).

#### Installation

```bash
# Install the latest version
pip install trigger

# Install in development mode
pip install -e ".[dev]"

# Using uv (faster)
uv pip install trigger
```

For users still requiring Python 2.7, use the v1.6.0 release:
```bash
pip install trigger==1.6.0
```

### Development Setup

Contributing to Trigger? Set up pre-commit hooks to catch issues early:

```bash
# Install prek (fast pre-commit framework)
uv tool install prek  # or: pip install prek

# Enable hooks in your clone
prek install

# Hooks will now run automatically on git commit
```

See [CLAUDE.md](CLAUDE.md) for complete development documentation.

### Upgrading from v1.6.0?

See the [Migration Guide](https://trigger.readthedocs.io/en/latest/migration.html) for detailed upgrade instructions.

### Before you begin

+ The [main](https://github.com/trigger/trigger/tree/main) branch is the
  primary branch for all development and releases. All pull requests target
  `main`.
+ Each point release of Trigger is maintained as a [tag](https://github.com/trigger/trigger/tags). If you require a
  specific Trigger version, please refer to these.

### Get in touch!

If you run into any snags, have questions, feedback, or just want to talk shop,
please open an issue on [GitHub Issues](https://github.com/trigger/trigger/issues).
