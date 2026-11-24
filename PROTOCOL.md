# Implementation Protocol

## Phase 1: Repository Analysis

Inspect:

- tinydb/table.py
- tinydb/database.py
- tests/
- project configuration
- existing exception conventions

Identify:

- All write operations.
- The common storage write mechanism.
- Current atomicity behavior.
- Existing test organization.

Output:

docs/ANALYSIS.md

Do not modify implementation files.

## Phase 2: Implementation Planning

Create:

docs/IMPLEMENTATION_PLAN.md

Include:

- Proposed architecture.
- Files to modify.
- Validation strategy.
- Test scenarios.
- Potential compatibility risks.

Verify that every acceptance criterion
has an implementation and test strategy.

## Phase 3: Implementation

Implement in small steps:

1. Add constraint registration.
2. Add uniqueness validation.
3. Integrate validation into write operations.
4. Add unit tests.
5. Update documentation.

Do not proceed to unrelated refactoring.

## Phase 4: Verification

Run:

- Relevant unit tests.
- Full pytest suite.
- Formatting and lint checks configured by the project.
- Type checking if configured.

Check:

- All acceptance criteria.
- Atomicity after failed writes.
- Compatibility with existing behavior.

## Phase 5: Final Review

Review the complete diff.

Check:

- No unrelated modifications.
- No duplicated validation logic.
- No missing write operations.
- No weakened tests.
- Documentation matches implementation.

## Phase 6: Completion

Produce:

docs/IMPLEMENTATION_REPORT.md

Include:

- Implemented functionality.
- Architecture decisions.
- Modified files.
- Tests executed.
- Actual test results.
- Unresolved issues.