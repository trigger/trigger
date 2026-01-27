# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trigger is a mature network automation toolkit written in Python for managing network devices at scale. Originally developed by AOL's Network Security team in 2006, it provides asynchronous command execution, ACL parsing/management, and metadata-driven device interaction across multiple vendor platforms (Cisco IOS/NX-OS/ASA, Juniper Junos/ScreenOS, Force10 FTOS, Arista, etc.).

**Key characteristics:**
- Python 3.10-3.11 codebase (v2.0.0+; Python 2.7 support ended with v1.6.0)
- Twisted-based asynchronous I/O framework
- Enterprise-scale network automation (hundreds to thousands of devices)
- Grammar-based ACL parsing and format conversion
- Redis-backed ACL database and deployment queue

## Development Commands

### Running Tests

**Unit tests:**
```bash
# Run all unit tests
pytest

# Run with verbose output
pytest -vv

# Run specific test file
pytest tests/test_acl.py

# Run with coverage
pytest --cov=trigger tests/
```

**Test environment variables** (automatically set by conftest.py):
- `TRIGGER_SETTINGS`: Path to test settings.py
- `NETDEVICES_SOURCE`: Path to test netdevices.xml
- `AUTOACL_FILE`: Path to test autoacl.py
- `BOUNCE_FILE`: Path to test bounce.py
- `TACACSRC`: Path to test tacacsrc credentials file
- `TACACSRC_KEYFILE`: Path to test tackf keyfile

### Linting

```bash
# Check code style (excludes packages/ directory)
flake8 trigger/ tests/ --exclude=trigger/packages --max-line-length=88

# Check formatting with black
black --check trigger/ tests/ --exclude 'trigger/packages'

# Check import sorting
isort --check-only trigger/ tests/ --skip trigger/packages
```

### Building and Installing

```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Install for production use
pip install .

# Build package distributions
python -m build

# Using uv (faster package manager)
uv pip install -e ".[dev]"
```

### Working with Twisted Plugins

After making changes to `twisted/plugins/trigger_xmlrpc.py`, regenerate the dropin.cache:
```bash
python -c "from twisted.plugin import IPlugin, getPlugins; list(getPlugins(IPlugin))"
```

## Architecture

### Core Component Layers

**1. Command Execution Layer (`trigger/cmds.py`)**
- `Commando` class: The primary abstraction for asynchronous multi-device command execution
- Subclass `Commando` and implement `to_{vendor}()` methods to generate commands and `from_{vendor}()` methods to parse results
- Automatically dispatches vendor-specific methods based on device metadata

**2. Device Metadata Layer (`trigger/netdevices/`)**
- `NetDevices`: Singleton dictionary of all managed network devices
- `NetDevice`: Individual device objects with attributes (vendor, model, type, ACLs, location, etc.)
- `Vendor`: Canonical vendor mapping (e.g., "cisco-ios" → "cisco")
- Pluggable loaders: filesystem (XML/JSON), MongoDB, RANCID, CSV

**3. Connection & Protocol Layer (`trigger/twister.py`, `trigger/twister2.py`)**
- `twister.py`: Original Twisted-based SSH/Telnet/Junoscript connections (~2,000 lines)
- `twister2.py`: Modern Crochet-based implementation bridging sync/async code
- Protocol handlers: `TriggerSSHChannelFactory`, `TriggerSSHGenericChannel`, `IoslikeSendExpect`
- Handles authentication, enable mode, command execution, and output capture

**4. ACL System (`trigger/acl/`)**
- Grammar-based parser using SimpleParse (BNF-style grammars)
- Object model: `ACL` → `Term` → `Matches` (IP addresses, ports, protocols)
- Format conversion between Cisco IOS, Juniper JunOS, and others
- `AclsDB`: Redis-based ACL-to-device mapping
- `ACLQueue`: Automated ACL deployment queue with manual/integrated workflows

**5. Configuration (`trigger/conf/`)**
- Django-style settings module loaded from `TRIGGER_SETTINGS` environment variable
- `global_settings.py`: All defaults (platforms, vendors, authentication, network definitions)
- Override settings by creating a custom settings.py and pointing `TRIGGER_SETTINGS` to it

### Key Design Patterns

- **Singleton**: `NetDevices` ensures device metadata is loaded once
- **Factory**: `vendor_factory()` caches `Vendor` objects
- **Strategy**: Vendor-specific behavior via `to_{vendor}()` / `from_{vendor}()` methods
- **Plugin Architecture**: Metadata loaders, Commando plugins
- **Asynchronous/Deferred**: Twisted Deferreds throughout for non-blocking I/O

### Data Flow: Command Execution

```
User Code (Commando subclass)
    ↓
NetDevices.find() → NetDevice object
    ↓
Device.execute() [dynamically bound by vendor]
    ↓
Credential retrieval (.tacacsrc)
    ↓
Protocol selection (SSH/Telnet/Junoscript)
    ↓
Twisted Channel creation
    ↓
Authentication & command execution
    ↓
from_{vendor}() result parsing
    ↓
Callback to user code
```

## Important Module Locations

- **`trigger/cmds.py`**: `Commando` class for multi-device command execution
- **`trigger/twister.py`**: SSH/Telnet connection handling, protocol implementations
- **`trigger/netdevices/__init__.py`**: Device metadata core (`NetDevices`, `NetDevice`)
- **`trigger/acl/parser.py`**: ACL grammar parser
- **`trigger/acl/support.py`**: ACL object model (`ACL`, `Term`, `Matches`)
- **`trigger/tacacsrc.py`**: Encrypted credential storage (GPG/legacy)
- **`trigger/changemgmt/bounce.py`**: Maintenance window management
- **`trigger/utils/`**: CLI helpers, network utilities, notifications, templates

## ACL System Usage

The ACL system supports parsing, validation, and format conversion:

```python
from trigger.acl import parse

# Parse an ACL from any supported format
acl = parse("access-list 123 permit tcp any host 10.20.30.40 eq 80")

# Name terms (required for Juniper output)
acl.name_terms()

# Convert to different format
junos_output = acl.output(format='junos')
ios_output = acl.output(format='ios')
```

**ACL Database Integration:**
- Explicit ACLs: Manually assigned to devices
- Implicit ACLs: Auto-assigned based on device attributes (via `autoacl.py`)
- Bulk ACLs: Large-scale policy sets
- Redis backend stores ACL-to-device mappings

## CLI Tools (bin/)

- **`acl`**: Work with ACL objects interactively
- **`aclconv`**: Convert ACLs between vendor formats
- **`check_access`**: Test if traffic would be permitted by an ACL
- **`find_access`**: Find ACL terms matching specific criteria
- **`load_acl`**: Deploy ACLs to devices
- **`netdev`**: Query device metadata from NetDevices
- **`run_cmds`**: Execute commands on multiple devices
- **`gong`**: Interactive device shell
- **`gnng`**: Advanced interactive device shell
- **`optimizer`**: Optimize ACLs (remove redundant terms)

## Dependencies & Version Constraints

- **Python 3.10-3.11** (v2.0.0+; Python 2.7 support ended with v1.6.0)
  - Python 3.12+ not yet supported due to SimpleParse C extension incompatibility
- **Twisted>=22.10.0**: Asynchronous networking framework
- **crochet>=2.0.0**: Sync/async bridging
- **pyparsing>=3.1.0**: ACL grammar parser
- **cryptography>=41.0.0**: Credential encryption
- **redis>=5.0.0**: ACL database backend
- **SimpleParse>=2.2.0**: BNF grammar parser for ACLs (Python 3.10-3.11 only)
- **textfsm>=1.1.0**: Template-based output parsing
- **pyasn1>=0.4.8**: ASN.1 parsing for SSH
- **IPy>=1.01**: IP address manipulation

## Testing Strategy

Tests are organized under `tests/`:
- `test_acl.py`: ACL parsing, conversion, and manipulation (~25K lines)
- `test_netdevices.py`: Device metadata and loaders
- `test_tacacsrc.py`: Credential storage
- `test_twister*.py`: Connection and protocol tests
- `tests/data/`: Mock configuration files (settings.py, netdevices.xml, etc.)
- `tests/acceptance/`: End-to-end acceptance tests

**Mock data for tests** is in `tests/data/`:
- `netdevices.xml`: Mock device inventory
- `settings.py`: Test configuration overrides
- `tacacsrc` / `tackf`: Mock credentials

## Configuration & Settings

Trigger uses environment variables to locate configuration:
- **`TRIGGER_SETTINGS`**: Path to settings.py (overrides defaults)
- **`NETDEVICES_SOURCE`**: Path to netdevices data source (XML/JSON file)
- **`AUTOACL_FILE`**: Path to autoacl.py (implicit ACL assignment logic)
- **`BOUNCE_FILE`**: Path to bounce.py (maintenance window definitions)
- **`TACACSRC`**: Path to .tacacsrc encrypted credentials file
- **`TACACSRC_KEYFILE`**: Path to TACACS key file

## Vendor Support

Trigger abstracts vendor differences through:
1. **Vendor mappings** in `global_settings.py` (e.g., "CISCO_LIKE", "JUNIPER_LIKE")
2. **Prompt patterns** for each vendor to detect command completion
3. **Dynamic method binding** on `NetDevice` objects (e.g., `device.execute()` dispatches to vendor-specific implementation)
4. **Format-specific ACL grammars** in `trigger/acl/`

Supported vendors include:
- Cisco IOS, IOS-XR, NX-OS, ASA
- Juniper Junos, ScreenOS (Netscreen)
- Arista EOS
- Force10 FTOS
- Brocade, Dell, Foundry
- A10, Citrix NetScaler
- F5 BigIP

## Common Gotchas

- **Python version**: Requires Python 3.10-3.11 (v2.0.0+); Python 3.12+ not yet supported due to SimpleParse
- **v2.0.0 breaking changes**: CLI tools now use entry points; credentials/config files unchanged
- **Twisted Deferreds**: Asynchronous patterns throughout; callbacks/errbacks required
- **ACL term naming**: Must call `acl.name_terms()` before outputting to Juniper format
- **Device metadata loading**: `NetDevices()` is a singleton; first instantiation loads all devices
- **Credentials**: Requires properly configured `.tacacsrc` file for device authentication
- **Vendor detection**: Based on device metadata, not auto-discovery; metadata must be accurate
- **Test isolation**: Tests use conftest.py to set environment variables for mock data

## Branch Strategy

- **`develop`**: Default branch, generally stable but not production-ready
- **`master`**: Stable production-ready branch
- Release tags: Specific versions available as tag branches (e.g., `v1.6.0`)
