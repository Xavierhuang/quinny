import re

_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def parse_semver(version):
    if not isinstance(version, str):
        raise TypeError("version must be a string")
    m = _SEMVER.match(version)
    if not m:
        raise ValueError(f"not a valid semver 2.0 string: {version!r}")
    major, minor, patch, pre, build = m.groups()
    return {
        "major": int(major),
        "minor": int(minor),
        "patch": int(patch),
        "prerelease": pre,
        "buildmetadata": build,
    }
