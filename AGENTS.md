# Project Agent Instructions

## Objective

Implement the feature described in SPEC.md
without introducing unnecessary architectural changes.

## Required Reading

Before starting:

1. Read CONSTITUTION.md.
2. Read SPEC.md.
3. Read PROTOCOL.md.
4. Read .claude/skills/python-feature/SKILL.md.
5. Inspect the existing project structure and relevant source code.

## Working Rules

- Do not modify code before completing the analysis.
- Follow the existing TinyDB architecture and conventions.
- Prefer minimal changes over architectural refactoring.
- Do not introduce external dependencies.
- Do not modify unrelated functionality.
- Do not weaken or remove existing tests.
- Do not change public APIs unless required by SPEC.md.
- Do not assume undocumented behavior.

## Implementation

1. Analyze the current Table implementation.
2. Identify all write operations.
3. Prepare an implementation plan.
4. Identify potential compatibility issues.
5. Implement the feature incrementally.
6. Add tests for every supported write operation.
7. Run relevant tests.
8. Run the complete test suite.

## Completion Report

Provide:

- Implementation summary.
- Modified files.
- Design decisions.
- Tests added.
- Commands executed.
- Actual test results.
- Known limitations.