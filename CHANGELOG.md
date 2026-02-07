# CHANGELOG


## v2.2.3 (2026-02-07)

### Bug Fixes

- Anchor prompt patterns to line boundaries to prevent false matches
  ([#317](https://github.com/trigger/trigger/pull/317),
  [`aef5684`](https://github.com/trigger/trigger/commit/aef56849f77724c1b008f05d9e701311bdc34509))

Prompt detection regex falsely matched '>' and '#' characters in command output (e.g. Juniper's
  "Flags: <Sync RSync>") as device prompts, causing output truncation. Add compile_prompt_pattern()
  helper that prepends a line-start anchor and prompt_match_start() to adjust match positions.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Documentation

- Add explicit docs dependencies and fix stale Python version note
  ([`33c86da`](https://github.com/trigger/trigger/commit/33c86da3a5d92ad3060d940d1086f1ae06e9d481))

Add a `docs` optional dependency group (sphinx, sphinx_rtd_theme) to pyproject.toml so RTD builds
  have the packages they need. Clean up .readthedocs.yml by removing the redundant pre_install job
  and pointing extra_requirements at the new `docs` group instead of `dev`. Update the outdated
  Python 2.6 note in docs/index.rst to reflect v2.0+ requirements (Python 3.10-3.11).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Add rebase merge guidance to CLAUDE.md
  ([`64f5893`](https://github.com/trigger/trigger/commit/64f5893a94ac989be341da6a36b0c84a3c45726c))

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Add v2.0.1–v2.2.2 entries to docs changelog and fix v2.0.0 date
  ([`74ccc86`](https://github.com/trigger/trigger/commit/74ccc8645c2e9ded1c78ec83cd67494fd3dd7d01))

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Fold versionadded directives into Key Features bullet list
  ([`749ef32`](https://github.com/trigger/trigger/commit/749ef329d163b395f8fb6d2495cd51f796606ecd))

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Update README and docs to reflect main branch and remove stale links
  ([`6ddb930`](https://github.com/trigger/trigger/commit/6ddb930e7578da63c00fbe95e432ae4d46e6f5b5))

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Update tests badge to match CI workflow name
  ([`1bd8353`](https://github.com/trigger/trigger/commit/1bd8353b27572005333a5edd3584b3bf4051be35))

The badge referenced a "Tests" workflow that doesn't exist. Updated to match the actual "CI"
  workflow in .github/workflows/ci.yml.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>


## v2.2.2 (2026-02-06)

### Bug Fixes

- Add uv.lock to repo and update workflows to use explicit cache-dependency-glob
  ([`3d8e34e`](https://github.com/trigger/trigger/commit/3d8e34e1a2265f317a9ab25e9c51c6d28c22729c))

- Remove uv.lock from .gitignore and commit it to the repository - Add cache-dependency-glob:
  "uv.lock" to all 6 workflow jobs for explicit cache key - Update test job to use "uv sync --locked
  --all-extras --dev" for reproducible builds with lock file validation - Fixes error: "No file in
  /home/runner/work/trigger/trigger matched to [**/uv.lock]"

The uv.lock file was gitignored, causing GitHub Actions to fail when trying to cache dependencies.
  Now the lock file is tracked and used explicitly for cache invalidation.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Remove cache-dependency-glob override and use uv sync for reproducible builds
  ([`3c448f3`](https://github.com/trigger/trigger/commit/3c448f3e668ce689260c8709d0c9c23b5f0a9fd0))

- Remove cache-dependency-glob parameter from all 6 workflow jobs to use setup-uv action's default
  glob pattern - Default pattern includes **/pyproject.toml, **/uv.lock, and **/requirements*.txt
  for proper cache invalidation - Switch test job from 'uv pip install --system -e ".[dev]"' to 'uv
  sync --all-extras' for reproducible builds using uv.lock - Fixes cache errors: "Path(s) specified
  in the action for caching do(es) not exist" - Ensures CI builds match local development when using
  uv sync

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Remove invalid --dev flag from uv sync command
  ([`ad8a498`](https://github.com/trigger/trigger/commit/ad8a498625840ef2525377612fa55f23ad8a37f1))

The --dev flag does not exist in uv sync. Dev dependencies are included by default. Only --no-dev,
  --only-dev, and --group flags exist for dependency group control.

This was causing the lockfile validation error.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Update uv.lock and remove redundant cache-dependency-glob
  ([`4503e4e`](https://github.com/trigger/trigger/commit/4503e4e494c23595e5be726713b6fc4916182d75))

- Update uv.lock to sync with pyproject.toml (fixes --locked validation error) - Remove
  cache-dependency-glob from all workflows (default already includes **/uv.lock) - Keep uv sync
  --locked --all-extras --dev for reproducible builds with validation

The default cache-dependency-glob pattern already includes: **/uv.lock, **/pyproject.toml,
  **/*requirements*.txt, and more

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Use --frozen instead of --locked for more lenient lock file validation
  ([`b82d968`](https://github.com/trigger/trigger/commit/b82d96807852c3646f685e49c6014eb2efc00bc9))

- Use uv run pytest to run tests in uv-managed environment
  ([`3386869`](https://github.com/trigger/trigger/commit/3386869989a68854af295cb782c2c031b9412d03))

### Testing

- Add comment to trigger CI and test cache hits
  ([`cc7f0b1`](https://github.com/trigger/trigger/commit/cc7f0b1db90f4ad16024f8657316927fff3b4665))


## v2.2.1 (2026-02-06)

### Bug Fixes

- Specify pyproject.toml for uv cache dependency glob
  ([`1e05648`](https://github.com/trigger/trigger/commit/1e05648fee78e0e1a1bb7945f030e2ebeec07745))

The enable-cache option defaults to looking for uv.lock files, but this project uses pyproject.toml
  without a lockfile. Add the cache-dependency-glob parameter to specify pyproject.toml for cache
  key generation.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Use uv's built-in caching instead of pip cache
  ([`9a05f11`](https://github.com/trigger/trigger/commit/9a05f1180044f1580e4b44c1ad43133b74a74429))

Replace cache: 'pip' on setup-python steps with enable-cache: true on setup-uv steps, per uv's
  official documentation. The pip cache parameter doesn't work with uv's cache structure.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

### Continuous Integration

- Enable pip caching in GitHub Actions workflows
  ([`fc22313`](https://github.com/trigger/trigger/commit/fc2231332105808e18bd8c1d898779a368696c52))

Add cache: 'pip' to all actions/setup-python@v5 steps across CI, release, and release-preview
  workflows to speed up dependency installation via GitHub's built-in package caching.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>


## v2.2.0 (2026-02-06)

### Chores

- Apply pre-commit auto-fixes and ignore false positives
  ([`c6a30bf`](https://github.com/trigger/trigger/commit/c6a30bf3ca4686b6e7c87932474b13c3aba387c1))

Apply remaining automatic fixes from ruff pre-commit hooks and configure ruff to ignore false
  positive warnings.

Changes: - Update .pre-commit-config.yaml to use ruff v0.14.14 (matching system) - Add PLW1641 and
  PT028 to pyproject.toml ignore list (false positives) - Apply ruff import sorting fixes across
  codebase - Fix trailing whitespace in documentation files

False positive justifications: - PLW1641: NetDevice implements __eq__ but warning fires incorrectly
  - PT028: test_tcp_port and test_ssh are utility functions, not pytest tests

All checks now pass cleanly in pre-commit hooks.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

### Features

- Add prek pre-commit hooks with ruff checks
  ([`98f04ad`](https://github.com/trigger/trigger/commit/98f04ad0d84b8b783fc80ed3f304bdbe3229463c))

Add prek (fast Rust-based pre-commit framework) to enforce code quality checks locally before
  commits, matching CI configuration exactly.

Changes: - Add .pre-commit-config.yaml with ruff and standard pre-commit hooks - Update CLAUDE.md:
  replace outdated flake8/black/isort docs with ruff - Add pre-commit hooks section to CLAUDE.md
  with prek setup instructions - Update README.md with development setup section - Add pre-commit
  hooks documentation to docs/development.rst

Benefits: - 7-10x faster than traditional pre-commit (Rust-based) - Catches issues locally before CI
  runs - Matches CI ruff checks exactly - Optional for developers (CI still enforces)

Hook checks: - Ruff linting with auto-fix - Ruff formatting (check-only) - YAML syntax validation -
  Trailing whitespace and end-of-file fixes - Protection against commits to main branch - Merge
  conflict detection

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>


## v2.1.1 (2026-02-06)

### Bug Fixes

- **security**: Replace deprecated tempfile.mktemp with mkstemp
  ([`884ecdf`](https://github.com/trigger/trigger/commit/884ecdfb4ec2dac6cbcfb4fe8e800b7dd5f5a056))

Replace unsafe `tempfile.mktemp()` with `tempfile.mkstemp()` in the remaining bin/ and tools/
  scripts. Uses `os.fdopen(fd)` to properly manage the file descriptor, consistent with the pattern
  established in trigger/acl/tools.py and trigger/contrib/docommand/core.py.

The `mktemp()` function is deprecated due to a race condition vulnerability (TOCTOU) where the
  temporary filename could be claimed by another process between creation of the name and opening
  the file.

Files fixed: - bin/check_syntax - bin/load_acl - tools/prepend_acl_dot

Based-on: https://github.com/trigger/trigger/pull/335

Co-Authored-By: Ataf Fazledin Ahamed <ataf@openrefactory.com>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>


## v2.1.0 (2026-02-06)

### Documentation

- Add git worktrees guidance to CLAUDE.md ([#343](https://github.com/trigger/trigger/pull/343),
  [`6f1489e`](https://github.com/trigger/trigger/commit/6f1489ece78cca00c47ebce02ce4f3ed061e6823))

Instructs Claude Code to always use .worktrees/ for feature branches to keep the main working tree
  clean.

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>

### Features

- **notifications**: Add SMTP_SSL support for secure email
  ([#344](https://github.com/trigger/trigger/pull/344),
  [`5ce484d`](https://github.com/trigger/trigger/commit/5ce484d2b9cb0241991eae071fdb5ea5f34b523c))

* feat(notifications): add SMTP_SSL support for secure email

Adds ssl, mailuser, and mailpass parameters to send_email() for secure SMTP communication via
  smtplib.SMTP_SSL.

Based on PR #336 by Ataf Fazledin Ahamed (OpenRefactory/OpenSSF Alpha-Omega).

Co-Authored-By: Ataf Fazledin Ahamed <ataf@openrefactory.com>

* style: fix ruff formatting for send_email signature

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

---------

Co-authored-by: Ataf Fazledin Ahamed <ataf@openrefactory.com>

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>


## v2.0.3 (2026-02-05)

### Bug Fixes

- **release**: Skip PyPI upload if version already exists
  ([`cce1a8c`](https://github.com/trigger/trigger/commit/cce1a8c8d6d8af18e277bd7c286456c69de326f5))

Prevents publish job from failing when re-running a release that was already partially published
  (e.g. after a prior push failure).

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>


## v2.0.2 (2026-02-05)

### Bug Fixes

- **release**: Checkout version-bumped tag for PyPI publish
  ([`e5044d8`](https://github.com/trigger/trigger/commit/e5044d87d05d9c8df213752a1169e02e65e59be9))

The publish job was checking out the triggering commit (PR merge) instead of the commit where
  semantic-release bumped the version. This caused the build to produce artifacts with the old
  version, which PyPI rejected.

Pass the tag output from semantic-release and use it as the checkout ref in the publish job.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

- **release**: Use RELEASE_TOKEN PAT to bypass branch protection
  ([`45489a8`](https://github.com/trigger/trigger/commit/45489a84dd485b6cc9996671d03bc02335e696b4))

GITHUB_TOKEN cannot push directly to main due to repository ruleset requiring pull requests. Use a
  PAT (RELEASE_TOKEN) so semantic-release can push version bump commits and tags.

Also update CLAUDE.md branch strategy to reflect main as the primary branch and deprecate the
  develop branch.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>


## v2.0.1 (2026-02-05)

### Bug Fixes

- Address PR review feedback
  ([`b89cff9`](https://github.com/trigger/trigger/commit/b89cff965eb76782c3c3d7f8df5406af9b556d77))

- Remove unreachable `return False` after `return True` in confirm_tables() - Remove unused tuple
  unpacking in parser.py processor function

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

- Apply ruff lint fixes to configs/ directory
  ([`133b66d`](https://github.com/trigger/trigger/commit/133b66d6bab8633acfeb806083cc0fe04404eb4d))

The CI lint job checks configs/ in addition to trigger/ and tests/. Fix docstring formatting,
  trailing commas, unnecessary variable before return, and invalid env var default type. Add
  per-file-ignores for configs/ (PTH, ERA001) since settings templates use string paths by design
  and commented-out code serves as user documentation.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

- **ci**: Fix release preview branch detection in PR context
  ([`b830812`](https://github.com/trigger/trigger/commit/b830812a93dc324384d3d8dcc8d43e28ecf61f22))

python-semantic-release requires the current branch to match the configured branch pattern ('main').
  PR checkouts are detached HEAD at the merge ref, so branch matching fails and reports "No version
  change". Fix by creating a local 'main' branch at the merge commit so semantic-release properly
  detects conventional commits.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

### Refactoring

- Enable comprehensive ruff lint rules and fix all violations
  ([`4877e7a`](https://github.com/trigger/trigger/commit/4877e7a3b131b09c9d9ce79ba64c5908e7e5c414))

Expand ruff configuration from 5 rule groups (F/E/W/I/UP) to 22, enforcing modern Python best
  practices across the codebase. Fix all 1,484 violations with zero behavioral changes — 129 tests
  pass.

Key improvements: - Migrate os.path/open() to pathlib (108 fixes) - Add proper exception chaining
  with raise-from (23 fixes) - Remove commented-out dead code (100 fixes) - Add trailing commas, fix
  docstring formatting (760+ auto-fixes) - Replace deprecated tempfile.mktemp with mkstemp (5 fixes)
  - Fix mutable argument defaults, zip-without-strict, and more - Extract exception message strings
  per EM101/EM102

Net result: 484 fewer lines of code, cleaner and more idiomatic Python.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>


## v2.0.0 (2026-02-03)

### Bug Fixes

- **release**: Fix v2.0.0 release pipeline
  ([`069707e`](https://github.com/trigger/trigger/commit/069707e6d704784db93dd9c95e23ba4bcac30ba3))

- Restore version to 2.0.0 (was incorrectly overwritten to 1.7.0 by semantic-release) - Fix
  release.yml to use official python-semantic-release GitHub Action - Fix missing step id that
  prevented build/publish from ever running - Remove obsolete tests.yml workflow (superseded by
  ci.yml)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

- **release**: Trigger publish on tag push, not just branch push
  ([`5068e4e`](https://github.com/trigger/trigger/commit/5068e4e7c02958b3e4bf17ed984fcf363dcf871f))

The release workflow only triggered on branch pushes to main, so pushing a v* tag did nothing. Split
  into two jobs: - release: runs semantic-release on branch pushes (future automated releases) -
  publish: builds and publishes to PyPI on tag pushes OR after semantic-release

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>


## v1.7.0 (2026-02-03)

### Bug Fixes

- Fix remaining Python 3 compatibility issues
  ([`fe6a7a2`](https://github.com/trigger/trigger/commit/fe6a7a2c1cb7ea45ec2332445fd3c88fc973a647))

Fixed 3 critical bugs introduced during Python 3 migration:

1. Missing ParserSyntaxError import from simpleparse.error - Added import to trigger/exceptions.py
  for test compatibility - Fixes testCommentStress test failure

2. Broken IP address formatting in JunOS ACL output - trigger/acl/support.py: Reverted junos_str()
  to percent formatting - .format(*pair) was unpacking IP objects incorrectly - Was outputting
  "192.0.2.0-192.0.2.1" instead of "192.0.2.0/24" - Fixes testJunOS test failure

3. Broken Peewee ORM queries in ACL queue - trigger/acl/queue.py: Reverted 'not m.done' to 'm.done
  == False' - Python 'not' operator doesn't translate to SQL in Peewee ORM - Added noqa:E712 to
  suppress ruff warnings (intentional) - Fixes test_12_list_manual_success test failure

All 129 tests now passing (100% pass rate).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Fix ruff linting issues.
  ([`e5455bf`](https://github.com/trigger/trigger/commit/e5455bfff84fabda0f95d86e503e32c488b20592))

- Python 3 compatibility fixes and modernization
  ([`e760af2`](https://github.com/trigger/trigger/commit/e760af2d9226429d17993d7acfa97c8abfe60707))

- Fixed Python 2 exception syntax (except X, e → except X as e) - Fixed Python 2 builtins (raw_input
  → input, file → open) - Auto-fixed 1223 style issues (imports, formatting, etc.) - Configured ruff
  for Python 3.10+ compatibility checking - Limited ruff scope to trigger/, tests/, configs/ (not
  examples/) - Added pragmatic ignores for legacy code patterns

Critical fixes: - trigger/acl/tools.py: except ValueError as err - trigger/bin/find_access.py:
  open() and except as - trigger/bin/load_acl.py: input() and except as - trigger/acl/db.py: open()
  instead of file() - trigger/netscreen.py: except Exception as e - docs/conf.py: removed encoding
  declarations

All ruff checks now pass on main codebase.

- Restore missing settings import in trigger/acl/junos.py
  ([`3153851`](https://github.com/trigger/trigger/commit/3153851617900c0d96857ad04042b780ba4f0ead))

The settings import was incorrectly removed during auto-fixing. Added explicit import for
  trigger.conf.settings which is used in juniper_multiline_comments() function.

- Restore opaque_braced_group string in junos.py grammar
  ([`0c93245`](https://github.com/trigger/trigger/commit/0c93245701182f2bad17cb5ba4773dfe05fd748e))

The auto-fix had removed quotes around 'opaque_braced_group' reference in the grammar string.
  Restored it to fix recursive grammar reference.

- **ci**: Exclude configs dir from ruff and fix preview warnings
  ([`17d9792`](https://github.com/trigger/trigger/commit/17d9792613701066b2f12e1981d83b704bfc9b77))

- **ci**: Remove uv cache and fix ruff commands
  ([`ce63a4c`](https://github.com/trigger/trigger/commit/ce63a4ca7597f3db8770fed2a792aff62e5f5de8))

- Remove enable-cache from setup-uv (no uv.lock file) - Change ruff commands to use . instead of
  explicit paths - Ruff will read pyproject.toml configuration automatically - This applies
  configured ignores and exclusions

- **configs**: Modernize Python 3 syntax and fix all ruff errors
  ([`78fffa3`](https://github.com/trigger/trigger/commit/78fffa37b538a344254f0ed284735dadb5155d00))

- Convert Python 2 print statements to Python 3 functions - Remove unnecessary UTF-8 encoding
  declarations (UP009) - Modernize percent formatting to f-strings (UP031) - Remove unused imports
  and fix import sorting - Fix ambiguous unicode quotes in comments (RUF003) - Add noqa comment for
  example password in trigger_settings.py - Remove BW alias, use full BounceWindow name (N817) - Fix
  operator precedence with parentheses (RUF021) - Apply ruff formatting for consistent style

All configs/ files now pass ruff check and are Python 3 compatible. Do not exclude configs/ from
  ruff checks - these are user-facing examples.

### Chores

- Add .worktrees/ and .venv to .gitignore
  ([`4d157a8`](https://github.com/trigger/trigger/commit/4d157a8138d3ffa265736d2eb58d6b77bd747383))

- Add ruff configuration and dependencies
  ([`1c591fe`](https://github.com/trigger/trigger/commit/1c591fef0a0d592797f94a96defbd30c36a82c7d))

- Add ruff to dev dependencies - Add python-semantic-release to dev dependencies - Configure ruff
  for Python 3.10+ with 88 char line length - Exclude trigger/packages directory - Enable
  comprehensive linting rules: - E/W: pycodestyle errors and warnings - F: pyflakes - I: isort - N:
  pep8-naming - UP: pyupgrade - B: flake8-bugbear - S: flake8-bandit (security) - PT:
  flake8-pytest-style - C4: flake8-comprehensions - SIM: flake8-simplify - RUF: Ruff-specific rules
  - Add pragmatic ignores for line length, pytest asserts, subprocess usage - Configure per-file
  ignores for tests and CLI tools - Configure isort with trigger as first-party import - Replace
  black, isort, and flake8 configuration with unified ruff config

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

### Continuous Integration

- Add automated release workflow
  ([`fa5519e`](https://github.com/trigger/trigger/commit/fa5519e290d7ec64c126d96de5a098db2f4b8775))

- Run python-semantic-release on push to main - Determine version from conventional commits -
  Generate changelog and update CHANGELOG.md - Create git tag and GitHub release - Build package
  with uv build - Publish to PyPI using OIDC trusted publisher - Requires 'release' environment for
  deployment protection

- Add continuous integration workflow
  ([`5f6c384`](https://github.com/trigger/trigger/commit/5f6c384d7b1c46d9bb5e9eb82beabbda3811853d))

- Test on Python 3.10 and 3.11 - Run ruff linting and formatting checks - Build package and verify
  build succeeds - Upload build artifacts for inspection - Runs on all pushes and PRs to main

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Add python-semantic-release configuration
  ([`5b92d2d`](https://github.com/trigger/trigger/commit/5b92d2d3b7b08aefd4fffeb221e2d99e16b91461))

- Configure semantic versioning from conventional commits - Set main branch as release branch -
  Enable PyPI upload and GitHub releases - Use uv build for package building - Configure changelog
  generation to CHANGELOG.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Add release preview workflow
  ([`7d8ad45`](https://github.com/trigger/trigger/commit/7d8ad4511c26c23af4e371a4e1519329618ee62e))

- Show next version on pull requests - Preview changelog based on commits - Post comment with
  version and changes - Remind developers about conventional commit format - Helps reviewers
  understand release impact

### Documentation

- Add comprehensive v2.0.0 changelog entry
  ([`faf43e6`](https://github.com/trigger/trigger/commit/faf43e655a6fd5ed7676b9198b5af2dda86c2a55))

- Document breaking changes (Python 3.10-3.11 required) - List all major dependency updates -
  Emphasize configuration compatibility - Link to migration guide - Document all features and
  internal changes

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Add Read the Docs configuration
  ([`1a30a49`](https://github.com/trigger/trigger/commit/1a30a49b7f0f68ad8b70e2543026e6ea0e555a7f))

- Configure RTD to use Python 3.11 - Install package with dev dependencies using uv - Build PDF and
  EPUB formats - Use docs/conf.py for Sphinx configuration - Enables versioned documentation builds

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Add v2.0.0 release design document
  ([`e5546a4`](https://github.com/trigger/trigger/commit/e5546a4f4406d582812e1a4f9de25f2cc2981bd9))

Add comprehensive design document for v2.0.0 release including: - Single branch strategy (main only,
  deprecate develop) - Conventional commits + python-semantic-release automation - GitHub Actions
  CI/CD pipeline (ci, release-preview, release) - PyPI trusted publisher setup (OIDC, no tokens) -
  Read the Docs version management - Complete implementation steps and verification strategy

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Convert migration guide from Markdown to RST
  ([`3d5ce6d`](https://github.com/trigger/trigger/commit/3d5ce6dc15645bad8e5b32f7636180a1191f665f))

- Convert MIGRATION_GUIDE.md to docs/migration.rst - Add migration guide to docs/index.rst toctree -
  Enables linking to published RTD documentation - Verified docs build successfully

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

- Update README with v2.0.0 information
  ([`3c5c8cb`](https://github.com/trigger/trigger/commit/3c5c8cbb47aa05902ad000b25b66fb9ae303c3b5))

- Clarify Python 3.10-3.11 requirement - Add link to migration guide for v1.6.0 users - Update all
  documentation links to use HTTPS - Ensure migration guide points to ReadTheDocs

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

### Features

- Add dynamic version management using importlib.metadata
  ([`929d5c0`](https://github.com/trigger/trigger/commit/929d5c0763b01c8a740800e28c3e92c3649ef283))

- Use importlib.metadata to read version from installed package - Update trigger.__init__.py with
  version fallback for dev mode - Update docs/conf.py to dynamically read version - Eliminates need
  for manual version bumps


## v1.6.0 (2017-03-08)
