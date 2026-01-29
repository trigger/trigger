# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-01-26

This is a major release that migrates Trigger from Python 2.7 to Python 3.10+.

**Python 2.7 support ended with v1.6.0.** This release requires Python 3.10 or 3.11.

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed upgrade instructions.

### Added

- **Python 3.10+ support**: Complete migration from Python 2.7 to Python 3.10-3.11
- **Modern packaging**: Migrated from setup.py to pyproject.toml (PEP 621)
- **CLI tools as entry points**: All 14 CLI tools (acl, netdev, gong, etc.) now installed as proper console entry points
- **GitHub Actions CI/CD**: Replaced Travis CI with GitHub Actions using uv for faster builds
- **Modern test infrastructure**: Migrated to pytest with conftest.py configuration
- **Code formatting**: Applied black formatter and isort to entire codebase

### Changed

- **Python version**: Now requires Python 3.10 or 3.11 (Python 3.12+ not yet supported due to SimpleParse)
- **CLI tool invocation**: Tools now installed as entry points instead of bin/ scripts
  - Old: `./bin/acl --help`
  - New: `acl --help`
- **Test runner**: `python setup.py test` → `pytest`
- **Build system**: `python setup.py install` → `pip install .`
- **Package name change**: `gtextfsm` → `textfsm`
- **Documentation**: Converted RST documentation to Markdown (README, LICENSE, AUTHORS, etc.)
- **Updated vendored packages**: peewee v2.1.4 → v3.17.0, tftpy Python 3 compatibility
- **Updated dependencies**:
  - Twisted: 15.5.0-16.x → ≥22.10.0
  - cryptography: ≥1.4 → ≥41.0.0
  - crochet: 1.5.0 → ≥2.0.0
  - pyparsing: ~2.2.0 → ≥3.1.0
  - redis: any → ≥5.0.0

### Removed

- setup.py, setup.cfg, requirements-dev.txt (use pyproject.toml)
- .travis.yml (use GitHub Actions)
- Python 2.7 support

### Fixed

- 200+ print statement conversions to print() functions
- 37 dictionary iterator methods (.iteritems → .items, etc.)
- 50+ old-style exception handlers
- 15 .has_key() calls → 'in' operator
- 13 basestring references → str
- Multiple import errors (StringIO, ConfigParser, urlparse)
- raise statement syntax in tftpy vendored package
- 48 deprecated metadata declarations from CLI tools

### Notes

- **String/bytes handling**: Python 3's strict str/bytes separation may require code changes in custom integrations
- **Configuration compatibility**: All configuration files remain compatible (settings.py, netdevices.xml/json, autoacl.py, bounce.py, .tacacsrc, environment variables)

## [1.6.0] - 2017-03-08

### Added

- Remote execution on devices running Cumulus Linux is now officially supported
- New configuration setting `DEFAULT_ADMIN_STATUS` (defaults to `PRODUCTION`)
- CLI-tool `gnng` now uses PTable instead of the old indent function
- Added -a/--listen-address option to the XMLRPC Server

### Changed

- PyCrypto has been replaced with the cryptography library
- The default NetDevices loader is now `JSONLoader`
- ACL support is now disabled by default (`WITH_ACLS = False`)
- The `conf` directory renamed to `configs` to avoid confusion with `trigger.conf`

### Fixed

- Fixed a bug in Cumulus Linux prompt patterns
- Disabled execution of `sudo vtysh` by default on Cumulus
- Bugfixes for handling esoteric SSH server implementations
- Bugfixes for the TextFSM parsed results bucket
- Fixed a bug on Arista EOS devices with prompt inclusion in results
- Use pyparsing~=2.2.0 for compat w/ setuptools>=34.0.0

---

For changes prior to v1.6.0, see [docs/changelog.rst](docs/changelog.rst).

[Unreleased]: https://github.com/trigger/trigger/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/trigger/trigger/compare/v1.6.0...v2.0.0
[1.6.0]: https://github.com/trigger/trigger/releases/tag/v1.6.0
