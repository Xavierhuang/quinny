"""Import a GitHub Spec Kit ``spec.md`` into a Quinny ``.qn`` contract.

Deterministic — no LLM. Spec Kit's structure maps directly onto Quinny's, so the
import is a pure parse:

  - ``# Feature Specification: <name>``     -> ``project``
  - each ``### User Story N - <title>``     -> a ``component`` whose Given/When/Then
    ``**Acceptance Scenarios**`` become gating ``test`` criteria (they are the
    concrete, checkable ones)
  - ``**FR-###**: System MUST ...``          -> ``constraint`` lines (behavioural
    intent — documents the impl, not concrete enough to gate reliably)
  - ``**SC-###**: <measurable outcome>``     -> advisory ``success`` lines

Unresolved ``[NEEDS CLARIFICATION: ...]`` markers are collected and reported,
never silently imported — an ambiguous line must not become a passing gate.
"""
from __future__ import annotations

import re

_FEATURE = re.compile(r"^#\s+Feature Specification:\s*(.+?)\s*$")
_STORY = re.compile(r"^###\s+User Story\s+\d+\s*[-–]\s*(.+?)\s*\(Priority:\s*(P\d+)\)\s*$")
_SCENARIO = re.compile(r"^\s*\d+\.\s+.*\*\*Given\*\*.+\*\*When\*\*.+\*\*Then\*\*.+$")
_FR = re.compile(r"^\s*[-*]\s+\*\*FR-\d+\*\*:\s*(.+?)\s*$")
_SC = re.compile(r"^\s*[-*]\s+\*\*SC-\d+\*\*:\s*(.+?)\s*$")
_H2 = re.compile(r"^##\s+")
_CLARIFY = re.compile(r"\[NEEDS CLARIFICATION:[^\]]*\]")
_BOLD = re.compile(r"\*\*(.+?)\*\*")


def _clean(s: str) -> str:
    """Strip markdown bold and collapse whitespace, keeping the prose."""
    s = _BOLD.sub(r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def _ident(title: str, fallback: str) -> str:
    """Turn a human title into a valid Quinny NAME (a CamelCase identifier)."""
    name = "".join(w[:1].upper() + w[1:] for w in re.findall(r"[A-Za-z0-9]+", title))
    if not name or not re.match(r"^[A-Za-z_]", name):
        return fallback
    return name


class ImportResult:
    def __init__(self, qn: str, clarifications: list[str], stats: dict[str, int]):
        self.qn = qn
        self.clarifications = clarifications
        self.stats = stats


def spec_to_qn(md: str) -> ImportResult:
    feature = "ImportedFeature"
    stories: list[dict] = []
    constraints: list[str] = []
    successes: list[str] = []
    clarifications: list[str] = []
    cur: dict | None = None

    for raw in md.splitlines():
        line = raw.rstrip()

        m = _FEATURE.match(line)
        if m:
            feature = _ident(m.group(1), "ImportedFeature")
            continue

        if _CLARIFY.search(line):
            # Never import a line that still needs clarification — report it.
            txt = _clean(_CLARIFY.sub("[…]", line)).lstrip("-*• ").strip()
            clarifications.append(txt or "(unspecified)")
            continue

        m = _STORY.match(line)
        if m:
            cur = {"name": _ident(m.group(1), f"Story{len(stories) + 1}"),
                   "title": _clean(m.group(1)), "goal": "", "tests": []}
            stories.append(cur)
            continue

        if _H2.match(line):
            cur = None  # left the user-story section; stop attaching to a story
            continue

        if _SCENARIO.match(line) and cur is not None:
            cur["tests"].append(_clean(re.sub(r"^\s*\d+\.\s*", "", line)))
            continue

        m = _FR.match(line)
        if m:
            constraints.append(_clean(m.group(1)))
            continue

        m = _SC.match(line)
        if m:
            successes.append(_clean(m.group(1)))
            continue

        # First plain prose line after a story header is its description (goal).
        # Skip bold labels (**Why**, **Independent Test**, ...), bullets, headings.
        if cur is not None and not cur["goal"]:
            txt = line.strip()
            if txt and txt[0] not in "*-#":
                cur["goal"] = _clean(txt)

    qn = _emit(feature, stories, constraints, successes)
    stats = {"stories": len(stories),
             "tests": sum(len(s["tests"]) for s in stories),
             "constraints": len(constraints),
             "successes": len(successes),
             "clarifications": len(clarifications)}
    return ImportResult(qn, clarifications, stats)


def _emit(feature: str, stories: list[dict],
          constraints: list[str], successes: list[str]) -> str:
    out: list[str] = [f"project {feature}", ""]
    for s in stories:
        out.append(f"component {s['name']}")
        out.append("    goal")
        out.append(f"        {s['goal'] or s['title']}")
        for t in s["tests"]:
            out.append("    test")
            out.append(f"        {t}")
        out.append("")
    if constraints or successes:
        out.append("component Requirements")
        out.append("    goal")
        out.append("        Feature-wide functional requirements and success "
                   "criteria imported from the Spec Kit specification.")
        for c in constraints:
            out.append("    constraint")
            out.append(f"        {c}")
        for sc in successes:
            out.append("    success")
            out.append(f"        {sc}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"
