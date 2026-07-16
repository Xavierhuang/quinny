"""Correct: normalizes the resolved path and asserts it stays under dest."""
import os


def safe_extract(entries: list[tuple[str, str]], dest_dir: str) -> None:
    dest_real = os.path.realpath(dest_dir)
    os.makedirs(dest_real, exist_ok=True)
    for name, content in entries:
        full = os.path.realpath(os.path.join(dest_real, name))
        # The Zip Slip fix: fail if the resolved path escapes dest.
        if not (full == dest_real or full.startswith(dest_real + os.sep)):
            raise ValueError(f"unsafe path: {name!r} escapes {dest_dir!r}")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
