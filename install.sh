#!/bin/sh
# Quinny installer.
#
#   curl -fsSL https://raw.githubusercontent.com/weijiahuang/quinny/main/install.sh | sh
#
# By default this installs the prebuilt, Python-free binary on Apple Silicon
# macOS, and falls back to `pipx`/`pip` everywhere else. Override with:
#
#   QUINNY_METHOD=pip     sh   # force the pip/pipx path (needs Python 3.10+)
#   QUINNY_METHOD=binary  sh   # force the binary path (Apple Silicon only)
#   QUINNY_VERSION=v0.1.0 sh   # install a specific tag instead of latest
#   QUINNY_PREFIX=/usr/local sh  # install under a different prefix
set -eu

REPO="weijiahuang/quinny"
PREFIX="${QUINNY_PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
LIB_DIR="$PREFIX/share/quinny"
METHOD="${QUINNY_METHOD:-auto}"

say()  { printf '%s\n' "$*"; }
info() { printf '\033[1m%s\033[0m\n' "$*"; }
warn() { printf '\033[33mwarning:\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

fetch_to() { # fetch_to URL FILE
  if have curl; then curl -fsSL "$1" -o "$2"
  elif have wget; then wget -qO "$2" "$1"
  else err "need curl or wget"; fi
}

detect_platform() {
  os=$(uname -s); arch=$(uname -m)
  case "$os" in
    Darwin) case "$arch" in arm64) PLATFORM="macos-arm64" ;; *) PLATFORM="" ;; esac ;;
    *) PLATFORM="" ;;
  esac
}

sha256_of() { # sha256_of FILE -> bare hash
  if have shasum; then shasum -a 256 "$1" | awk '{print $1}'
  elif have sha256sum; then sha256sum "$1" | awk '{print $1}'
  else echo ""; fi
}

install_binary() {
  [ -n "$PLATFORM" ] || err "no prebuilt binary for $(uname -s)/$(uname -m); re-run with QUINNY_METHOD=pip"
  asset="quinny-$PLATFORM.tar.gz"
  if [ "${QUINNY_VERSION:-latest}" = "latest" ]; then
    base="https://github.com/$REPO/releases/latest/download"
  else
    base="https://github.com/$REPO/releases/download/$QUINNY_VERSION"
  fi

  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  info "Downloading $asset ..."
  fetch_to "$base/$asset" "$tmp/$asset" || err "download failed (is the release published?)"

  # Verify checksum if the .sha256 asset is present.
  if fetch_to "$base/$asset.sha256" "$tmp/$asset.sha256" 2>/dev/null; then
    want=$(awk '{print $1}' "$tmp/$asset.sha256")
    got=$(sha256_of "$tmp/$asset")
    if [ -n "$got" ] && [ -n "$want" ] && [ "$got" != "$want" ]; then
      err "checksum mismatch (expected $want, got $got)"
    fi
    [ -n "$got" ] && say "Checksum OK."
  else
    warn "no checksum asset found; skipping verification"
  fi

  info "Installing to $LIB_DIR ..."
  rm -rf "$LIB_DIR"
  mkdir -p "$LIB_DIR" "$BIN_DIR"
  tar -xzf "$tmp/$asset" -C "$LIB_DIR"
  # The tarball holds a single top-level dir; find the launcher inside it.
  launcher=$(find "$LIB_DIR" -maxdepth 2 -type f -name 'quinny*' -perm -u+x | head -n1)
  [ -n "$launcher" ] || err "could not find the quinny launcher in the archive"
  # Downloaded-file quarantine would trip Gatekeeper; clear it (best effort).
  if have xattr; then xattr -dr com.apple.quarantine "$LIB_DIR" 2>/dev/null || true; fi
  chmod +x "$launcher"
  ln -sf "$launcher" "$BIN_DIR/quinny"
  DONE_PATH="$BIN_DIR/quinny"
}

install_pip() {
  if have pipx; then
    info "Installing with pipx ..."
    pipx install quinny
    DONE_PATH="$(command -v quinny || echo "$HOME/.local/bin/quinny")"
  elif have python3; then
    info "Installing with pip (--user) ..."
    python3 -m pip install --user --upgrade quinny
    DONE_PATH="$(command -v quinny || echo "$BIN_DIR/quinny")"
  else
    err "need pipx or python3 (3.10+) for the pip install path"
  fi
}

main() {
  detect_platform
  case "$METHOD" in
    binary) install_binary ;;
    pip)    install_pip ;;
    auto)   if [ -n "$PLATFORM" ]; then install_binary; else
              say "No prebuilt binary for this platform — using pip."
              install_pip
            fi ;;
    *) err "unknown QUINNY_METHOD='$METHOD' (use auto|binary|pip)" ;;
  esac

  # PATH hint.
  case ":$PATH:" in
    *":$BIN_DIR:"*) : ;;
    *) warn "$BIN_DIR is not on your PATH. Add it, e.g.:"
       say  "    echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.zshrc && source ~/.zshrc" ;;
  esac

  info "Installed. Try:  quinny --help"
}

main "$@"
