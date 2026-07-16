"""Buggy: naive os.path.join, no traversal check. Matches the pre-fix code
of many pre-2018 tar/zip libraries."""
import os


def safe_extract(entries: list[tuple[str, str]], dest_dir: str) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    for name, content in entries:
        # Bug: `../evil.txt` slides right past this — os.path.join happily
        # follows `..` segments and absolute paths.
        full = os.path.join(dest_dir, name)
        os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
