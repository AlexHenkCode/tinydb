# Project Constitution

## 1. Code Integrity

- Preserve existing public API behavior.
- Preserve backward compatibility.
- Do not introduce unnecessary abstractions.
- Follow existing naming and coding conventions.
- Avoid unrelated refactoring.

## 2. Architecture

- Respect existing separation of responsibilities.
- Keep feature logic close to the existing Table write operations.
- Do not introduce a separate database engine or storage layer.
- Avoid duplicating validation logic.

## 3. Data Integrity

- A failed write must not partially modify stored data.
- A failed update must not leave the table in an invalid state.
- All writes must respect active unique constraints.
- Batch operations must be validated as a whole.

## 4. Testing

- Every new behavior requires automated tests.
- Existing tests must continue to pass.
- Do not skip failing tests.
- Do not replace meaningful assertions with weaker ones.
- Test both successful and rejected operations.

## 5. Agent Discipline

- Never invent test results.
- Never claim implementation is complete without verification.
- Report unresolved questions explicitly.
- Ask for clarification when requirements conflict.