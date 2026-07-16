"""Spec Kit spec.md -> .qn import is a deterministic, valid-contract parse."""
from quinny.parser import parse
from quinny.speckit import spec_to_qn

SPEC = """\
# Feature Specification: URL Shortener

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Shorten a URL (Priority: P1)

A visitor pastes a long URL and receives a short code.

**Why this priority**: Core value.

**Acceptance Scenarios**:

1. **Given** a valid URL, **When** submitted, **Then** a unique short code is returned.
2. **Given** the same URL again, **When** submitted, **Then** the same code is returned.

### User Story 2 - Redirect (Priority: P2)

A visitor opens a short code and is redirected.

**Acceptance Scenarios**:

1. **Given** an existing code, **When** requested, **Then** they are redirected.

### Edge Cases

- What happens when the URL is malformed?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST reject inputs that are not valid URLs.
- **FR-002**: System MUST authenticate admins via [NEEDS CLARIFICATION: method?].

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A code resolves in under 50ms at the median.
"""


def test_import_maps_structure():
    res = spec_to_qn(SPEC)
    assert res.stats == {"stories": 2, "tests": 3, "constraints": 1,
                         "successes": 1, "clarifications": 1}


def test_stories_become_components_with_gating_tests():
    qn = spec_to_qn(SPEC).qn
    assert "project URLShortener" in qn
    assert "component ShortenAURL" in qn
    assert "component Redirect" in qn
    # Given/When/Then acceptance scenarios become gating `test` criteria.
    assert qn.count("    test\n") == 3
    assert "Given a valid URL, When submitted, Then a unique short code" in qn


def test_fr_constraint_sc_success_mapping():
    qn = spec_to_qn(SPEC).qn
    assert "    constraint\n        System MUST reject inputs" in qn
    assert "    success\n        A code resolves in under 50ms" in qn


def test_needs_clarification_is_skipped_not_imported():
    res = spec_to_qn(SPEC)
    # The ambiguous FR must NOT appear as a constraint (it can't be a gate yet).
    assert "authenticate admins" not in res.qn
    assert res.clarifications and "authenticate admins" in res.clarifications[0]


def test_emitted_contract_parses():
    # The whole point of the wedge: the import yields a VALID Quinny contract.
    project = parse(spec_to_qn(SPEC).qn)
    assert project.name == "URLShortener"
    assert len(project.declarations) == 3
