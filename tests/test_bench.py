"""End-to-end test of the benchmark harness — stubs the Anthropic client so
the whole pipeline (plan → generate → fast+full verify → assemble → run
main.py) executes without any real API calls.

Purpose: prove the harness plumbing is correct before spending real tokens.
When the user does run the live benchmark with an API key, any regression
here would show up as a stubbed-test failure first.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

# Make sure the scripts/ directory is importable so we can call bench.run_one
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import bench  # noqa: E402


# -------------------- Stubbed Anthropic client --------------------

@dataclass
class _StubUsage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class _StubBlock:
    type: str
    text: str


@dataclass
class _StubResponse:
    content: list[_StubBlock]
    usage: _StubUsage


class _StubMessages:
    """Returns hand-crafted realistic Python for the todo_service prompt."""

    def create(self, **kwargs) -> _StubResponse:
        prompt = kwargs["messages"][0]["content"]
        text = _canned_reply(prompt)
        # Realistic-ish token counts so the accounting has real numbers to
        # aggregate. Input scales with prompt length; output with reply.
        return _StubResponse(
            content=[_StubBlock(type="text", text=text)],
            usage=_StubUsage(
                input_tokens=max(200, len(prompt) // 4),
                output_tokens=max(100, len(text) // 4),
            ),
        )


class _StubClient:
    def __init__(self) -> None:
        self.messages = _StubMessages()


_CANNED_RAW = (
    "```python\n"
    "# main.py\n"
    "def add(x: int, y: int) -> int:\n"
    "    return x + y\n"
    "\n"
    "if __name__ == '__main__':\n"
    "    assert add(1, 2) == 3\n"
    "    print('ok')\n"
    "```\n"
)


def _canned_reply(prompt: str) -> str:
    """Pick a plausible reply based on which stage the prompt belongs to."""
    if "Emit the project now" in prompt or "Requirement:" in prompt:
        return _CANNED_RAW
    if "shared_types.py" in prompt and "Emit `shared_types.py`" in prompt:
        return (
            "from dataclasses import dataclass\n\n"
            "@dataclass(frozen=True)\n"
            "class Todo:\n"
            "    id: int\n"
            "    title: str\n"
        )
    if "Filename for this node:" in prompt:
        # Which node? Pull the filename out of the prompt so we return the
        # right file body.
        line = next(l for l in prompt.splitlines()
                    if l.startswith("Filename for this node:"))
        fname = line.split(":", 1)[1].strip()
        return _CANNED_FILES.get(fname, "# empty\n")
    if "Emit main.py" in prompt or "main.py that ties everything" in prompt:
        return _CANNED_MAIN
    # Repair call — return the original file unchanged (test doesn't exercise
    # repair since our canned files pass verification).
    return "# noop\n"


_CANNED_FILES: dict[str, str] = {
    "store.py": (
        "from shared_types import Todo\n\n"
        "_store: dict[int, Todo] = {}\n"
        "_next_id = 1\n\n"
        "def put(title: str) -> Todo:\n"
        "    global _next_id\n"
        "    todo = Todo(id=_next_id, title=title)\n"
        "    _store[todo.id] = todo\n"
        "    _next_id += 1\n"
        "    return todo\n\n"
        "def get_all() -> list[Todo]:\n"
        "    return list(_store.values())\n\n"
        "def drop(todo_id: int) -> bool:\n"
        "    return _store.pop(todo_id, None) is not None\n\n"
        'if __name__ == "__main__":\n'
        "    assert get_all() == []\n"
    ),
    "add_todo.py": (
        "import store\n\n"
        "def add(title: str) -> int:\n"
        "    return store.put(title).id\n\n"
        'if __name__ == "__main__":\n'
        '    assert add("hello") > 0\n'
    ),
    "list_todos.py": (
        "import store\n\n"
        "def list_all():\n"
        "    return store.get_all()\n\n"
        'if __name__ == "__main__":\n'
        "    _ = list_all()\n"
    ),
    "remove_todo.py": (
        "import store\n\n"
        "def remove(todo_id: int) -> bool:\n"
        "    return store.drop(todo_id)\n\n"
        'if __name__ == "__main__":\n'
        "    assert remove(999) is False\n"
    ),
}

_CANNED_MAIN = (
    "from add_todo import add\n"
    "from list_todos import list_all\n"
    "from remove_todo import remove\n\n"
    'if __name__ == "__main__":\n'
    "    a = add('first')\n"
    "    b = add('second')\n"
    "    items = list_all()\n"
    "    assert len(items) == 2\n"
    "    assert remove(a) is True\n"
    "    assert len(list_all()) == 1\n"
    "    print('todo service OK')\n"
)


# The stub Quinny plan matches the canned files above.
_STUB_PLAN = (
    "project TodoService\n\n"
    "component Store\n"
    "    goal\n"
    "        In-memory storage for todos.\n\n"
    "task AddTodo\n"
    "    goal\n"
    "        Append a todo, return its id.\n"
    "    input\n"
    "        title\n"
    "    output\n"
    "        todo_id\n"
    "    depends\n"
    "        Store\n"
    "    test\n"
    "        A fresh add returns a positive id.\n\n"
    "task ListTodos\n"
    "    goal\n"
    "        Return every todo currently stored.\n"
    "    output\n"
    "        todos\n"
    "    depends\n"
    "        Store\n"
    "    test\n"
    "        Empty store returns an empty list.\n\n"
    "task RemoveTodo\n"
    "    goal\n"
    "        Delete a todo by id; return whether it existed.\n"
    "    input\n"
    "        todo_id\n"
    "    depends\n"
    "        Store\n"
    "    test\n"
    "        Removing a missing id returns False.\n"
)


# --------------------------- The test ---------------------------

@pytest.fixture
def stubbed(monkeypatch, tmp_path):
    """Point bench.* at a tmp dir and stub anthropic.Anthropic() everywhere."""
    monkeypatch.setattr(bench, "PROMPTS_DIR", tmp_path / "prompts")
    monkeypatch.setattr(bench, "PLANS_DIR",   tmp_path / "plans")
    monkeypatch.setattr(bench, "WORK_DIR",    tmp_path / ".work")
    (tmp_path / "prompts").mkdir()
    (tmp_path / "plans").mkdir()
    prompt = tmp_path / "prompts" / "todo_service.txt"
    prompt.write_text("A tiny in-memory todo service.\n")
    (tmp_path / "plans" / "todo_service.qn").write_text(_STUB_PLAN)

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **kw: _StubClient())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub-key-for-tests")
    return prompt


def test_bench_run_one_end_to_end(stubbed):
    """Full plumbing: generate + verify + assemble + `python main.py`."""
    r = bench.run_one(stubbed, "all-opus", run_index=0)
    assert r.error == "", r.error
    # 4 declarations in the stub plan + 1 shared_types.py = 5 files.
    assert r.files_generated == 5, f"expected 5, got {r.files_generated}"
    assert r.verify_passed == 5, f"fast verify: {r.verify_passed}/5"
    assert r.full_verified == 5, f"full verify: {r.full_verified}/5"
    assert r.main_runs is True, "python main.py should exit 0"
    # Token accounting picked up every stubbed call.
    assert r.tokens_input > 0 and r.tokens_output > 0
    assert r.tokens_total == r.tokens_input + r.tokens_output


def test_bench_run_one_records_missing_plan(stubbed, tmp_path):
    """A prompt with no cached plan should surface a clear error, not crash."""
    other = tmp_path / "prompts" / "unknown.txt"
    other.write_text("something\n")
    r = bench.run_one(other, "all-opus", run_index=0)
    assert "no cached plan" in r.error
    assert r.files_generated == 0
    assert r.main_runs is False


def test_bench_raw_baseline_end_to_end(stubbed):
    """Raw-prompt path: stubbed Claude returns a working single-file project."""
    r = bench.run_one(stubbed, "raw-opus", run_index=0)
    assert r.error == "", r.error
    assert r.files_generated >= 1
    assert r.main_runs is True
    assert r.tokens_total > 0


def test_bench_raw_parse_extracts_multi_file():
    """_parse_raw_files handles multiple ```python # foo.py\\n...``` blocks."""
    reply = (
        "```python\n# helpers.py\ndef hi():\n    return 'hi'\n```\n\n"
        "```python\n# main.py\nfrom helpers import hi\nprint(hi())\n```\n"
    )
    files = bench._parse_raw_files(reply)
    assert set(files) == {"helpers.py", "main.py"}
    assert "def hi" in files["helpers.py"]


def test_bench_summary_prints_without_crashing(stubbed, capsys):
    """Aggregation + printing shouldn't blow up on a small result set."""
    r1 = bench.run_one(stubbed, "all-opus", run_index=0)
    r2 = bench.run_one(stubbed, "opus+haiku", run_index=0)
    bench.print_summary([r1, r2])
    out = capsys.readouterr().out
    assert "BENCHMARK SUMMARY" in out
    assert "all-opus" in out
    assert "opus+haiku" in out
