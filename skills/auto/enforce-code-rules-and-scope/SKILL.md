---
name: enforce-code-rules-and-scope
description: Use when modifying codebase files, fixing bugs, or implementing tests to ensure scope boundaries and all requirements are respected.
---
1. **Never modify original test files**: Leave existing files in `tests/` untouched. Add new test files (e.g., `tests/test_regressions.py`) for custom tests.
2. **Type annotations**: Ensure every public function (names not starting with `_`) has full type annotations on all parameters and return values.
3. **Regression tests**: Add at least one test function per bug fixed in the designated regression test file, and run pytest to confirm all tests pass.
4. **Changelog updates**: Record each fix in `CHANGELOG.md` under the `## Unreleased` heading using the standard bullet format: `- fix(<function name>): <short description>`.
