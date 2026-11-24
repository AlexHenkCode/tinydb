---
name: python-feature
description: Implement and test features in existing Python projects.
---

# Python Feature Development

## 1. Repository First

Before implementation:

- Inspect pyproject.toml.
- Inspect pytest configuration.
- Identify supported Python versions.
- Inspect existing code conventions.
- Reuse existing abstractions where appropriate.

Never assume dependencies or tooling.

## 2. Python Coding Rules

- Follow PEP 8.
- Use type hints for public methods.
- Use descriptive names.
- Keep functions focused.
- Prefer simple control flow.
- Avoid unnecessary inheritance.
- Avoid unnecessary abstractions.
- Preserve existing exception conventions.
- Add docstrings to public APIs.

## 3. Testing Rules

Use pytest if configured.

For each feature:

- Test normal behavior.
- Test boundary conditions.
- Test invalid input.
- Test exception behavior.
- Test regression scenarios.
- Test atomicity where applicable.

Tests must verify observable behavior,
not internal implementation details.

## 4. Test Design

Prefer parametrized tests for similar scenarios.

Test both:

- Positive cases.
- Negative cases.

For database features, verify persisted state
after successful and failed operations.

## 5. Compatibility

- Preserve existing public interfaces.
- Avoid changing default behavior.
- Do not introduce dependencies without approval.
- Test compatibility with existing functionality.

## 6. Documentation

Update existing documentation conventions.

Document public APIs, parameters,
exceptions and behavioral limitations.

## 7. Code Quality

Before completion:

- Run formatter if configured.
- Run linter if configured.
- Run type checker if configured.
- Run pytest.
- Review git diff.

Never report a check as successful
unless it was actually executed.