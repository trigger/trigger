# Ruff Modernization Design

**Status:** Approved
**Date:** 2026-02-04

## Goal

Enable a comprehensive set of ruff lint rules beyond the current baseline (F, E, W, I, UP) to enforce modern Python best practices across the Trigger codebase. This is a patch-level change — no API or behavioral changes.

## Rules Enabled

| Prefix | Category | Rationale |
|--------|----------|-----------|
| B | flake8-bugbear | Real bug prevention (mutable defaults, raise-from, zip-strict) |
| COM | flake8-commas | Trailing comma consistency |
| D | pydocstyle | Docstring formatting + punctuation |
| EM | flake8-errmsg | Exception message hygiene |
| ERA | eradicate | Remove commented-out dead code |
| F | pyflakes | (existing) |
| FURB | refurb | Modern Python idioms |
| I | isort | (existing) |
| PERF | perflint | Performance patterns |
| PIE | flake8-pie | Unnecessary placeholders/range starts |
| PLR | pylint-refactor | Collapsible if/else, useless returns |
| PLW | pylint-warnings | Useless else on loops |
| PT | flake8-pytest | Pytest-style assertions |
| PTH | flake8-use-pathlib | pathlib migration |
| RET | flake8-return | Superfluous else, unnecessary returns |
| RSE | flake8-raise | Unnecessary parens on raise |
| RUF | ruff-specific | f-string conversions, unsorted __all__, chained operators |
| S | flake8-bandit | Targeted security fixes |
| SIM | flake8-simplify | Code simplification |
| UP | pyupgrade | (existing) |
| E | pycodestyle errors | (existing) |
| W | pycodestyle warnings | (existing) |

## Rules Explicitly Ignored

| Rule | Reason |
|------|--------|
| ANN* | Type annotations — massive retrofit, skip entirely |
| T201 | Print statements — CLI toolkit uses print() legitimately |
| N* | Naming — Twisted camelCase conventions, can't change |
| FBT* | Boolean traps — API-breaking to fix |
| C901 | Complexity — deep refactoring territory |
| PLR0911/0912/0913/0915 | Too-many-* — same |
| PLR2004 | Magic value comparison — too noisy |
| PLW0603 | Global statements — parser pattern, leave alone |
| TD*/FIX* | TODO tags — informational, not enforced |
| S101 | assert — used in tests |
| S105/S110/S112 | Security false positives for this codebase |
| S314/S603/S605/S606/S608 | Shell/subprocess — fix manually, not as lint rule |
| SLF001 | Private member access — common in Twisted patterns |
| RUF012 | Mutable class default — too many in device metadata |
| D100-D107 | Missing docstrings — not enforcing docstring coverage |
| D200/D205/D401/D402/D404 | Docstring content style — too opinionated |
| B016/B018 | Raise-literal/useless-expression — used in tests |

## Execution Phases

### Phase 1: Config update + safe auto-fixes (~760 fixes)
- Update pyproject.toml with new select/ignore lists
- Run `ruff check --fix trigger/ tests/`
- Commit

### Phase 2: Unsafe auto-fixes (~1,750 fixes)
- Run `ruff check --fix --unsafe-fixes trigger/ tests/`
- Run test suite to verify
- Commit

### Phase 3: Manual fixes (remaining violations)
- pathlib migration (PTH)
- `raise` without `from` (B904)
- Mutable defaults (B006)
- Commented-out code removal (ERA001)
- Targeted security fixes (mktemp, os.popen, eval)
- Commit

### Phase 4: Verify and tune ignores
- Run full test suite
- Add any unanticipated false positives to ignore list
- Goal: `ruff check` passes clean
- Commit

Each phase gets its own commit for easy bisection.
