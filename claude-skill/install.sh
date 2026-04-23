#!/usr/bin/env bash
# Installer for the dehashed-recon Claude Code skill and its /dehashed slash command.
#
# Usage:
#   cd path/to/dehashed-recon
#   ./install.sh
#
# What it does:
#   1. Verifies python3 and pip are available.
#   2. Installs the Python deps the skill scripts need (requests, openpyxl).
#   3. Copies the skill into ~/.claude/skills/dehashed-recon/
#   4. Copies the slash command into ~/.claude/commands/dehashed.md
#   5. Smoke-tests the query script with --help
#   6. Reports API key discovery status and next-step guidance.
#
# Idempotent: re-running is safe. An existing install is backed up to
# <target>.bak-<timestamp> before overwrite. If the script is being run from
# inside the already-installed location, the copy step is skipped to avoid
# self-destruction.
#
# Flags:
#   --no-deps   Skip pip install (use if you've already installed requests/openpyxl)
#   --quiet     Suppress info-level output (errors still print)

set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_TARGET="$HOME/.claude/skills/dehashed-recon"
CMD_TARGET="$HOME/.claude/commands/dehashed.md"

INSTALL_DEPS=1
QUIET=0
for arg in "$@"; do
  case "$arg" in
    --no-deps) INSTALL_DEPS=0 ;;
    --quiet) QUIET=1 ;;
    -h|--help)
      sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//' | head -n -1
      exit 0
      ;;
    *) echo "Unknown flag: $arg" >&2; exit 2 ;;
  esac
done

log()  { [[ $QUIET -eq 1 ]] || echo "[*] $*"; }
ok()   { [[ $QUIET -eq 1 ]] || echo "[+] $*"; }
warn() { echo "[!] $*" >&2; }
die()  { echo "[!] $*" >&2; exit 1; }

log "Source: $SOURCE_DIR"

# --- 1. Sanity check source layout --------------------------------------------
for required in SKILL.md scripts/dehashed_query.py scripts/to_xlsx.py references/query-syntax.md command/dehashed.md; do
  [[ -f "$SOURCE_DIR/$required" ]] || die "Missing source file: $required (run from the dehashed-recon directory)"
done

# --- 2. Python + deps ---------------------------------------------------------
command -v python3 >/dev/null 2>&1 || die "python3 not found on PATH"

if [[ $INSTALL_DEPS -eq 1 ]]; then
  log "Installing Python deps (requests, openpyxl)..."
  if ! python3 -c "import pip" >/dev/null 2>&1; then
    die "pip not available for python3. Install pip first or re-run with --no-deps."
  fi
  if ! python3 -m pip install --user --quiet --upgrade requests openpyxl; then
    warn "--user install failed; retrying without --user"
    python3 -m pip install --quiet --upgrade requests openpyxl
  fi
  ok "Deps installed"
else
  log "Skipping dep install (--no-deps)"
fi

# --- 3. Install skill ---------------------------------------------------------
backup_existing() {
  local path="$1"
  if [[ -e "$path" ]]; then
    local bak="${path}.bak-$(date +%Y%m%d%H%M%S)"
    mv "$path" "$bak"
    log "Backed up existing $path -> $bak"
  fi
}

# If the script is running from inside the target (i.e. the working copy IS the
# installed copy), skip the copy — that would move the source to a backup and
# leave the target empty. Detect via resolved absolute paths.
SOURCE_REAL="$(cd "$SOURCE_DIR" && pwd -P)"
TARGET_REAL=""
if [[ -d "$SKILL_TARGET" ]]; then
  TARGET_REAL="$(cd "$SKILL_TARGET" && pwd -P)"
fi

if [[ -n "$TARGET_REAL" && "$SOURCE_REAL" == "$TARGET_REAL" ]]; then
  log "Source == target ($TARGET_REAL); skill already installed in place, skipping copy."
  rm -rf "$SKILL_TARGET/scripts/__pycache__" 2>/dev/null || true
  chmod +x "$SKILL_TARGET/scripts/dehashed_query.py" "$SKILL_TARGET/scripts/to_xlsx.py" 2>/dev/null || true
else
  log "Installing skill -> $SKILL_TARGET"
  backup_existing "$SKILL_TARGET"
  mkdir -p "$SKILL_TARGET"
  cp "$SOURCE_DIR/SKILL.md" "$SKILL_TARGET/"
  cp -r "$SOURCE_DIR/scripts" "$SKILL_TARGET/"
  cp -r "$SOURCE_DIR/references" "$SKILL_TARGET/"
  rm -rf "$SKILL_TARGET/scripts/__pycache__" 2>/dev/null || true
  chmod +x "$SKILL_TARGET/scripts/dehashed_query.py" "$SKILL_TARGET/scripts/to_xlsx.py"
  ok "Skill files in place"
fi

# --- 4. Install slash command -------------------------------------------------
log "Installing slash command -> $CMD_TARGET"
backup_existing "$CMD_TARGET"
mkdir -p "$(dirname "$CMD_TARGET")"
cp "$SOURCE_DIR/command/dehashed.md" "$CMD_TARGET"
ok "Slash command /dehashed registered"

# --- 5. Smoke test ------------------------------------------------------------
log "Smoke-testing query script..."
if python3 "$SKILL_TARGET/scripts/dehashed_query.py" --help >/dev/null 2>&1; then
  ok "dehashed_query.py --help OK"
else
  die "dehashed_query.py --help failed — install is broken"
fi
if python3 "$SKILL_TARGET/scripts/to_xlsx.py" --help >/dev/null 2>&1; then
  ok "to_xlsx.py --help OK"
else
  die "to_xlsx.py --help failed — install is broken"
fi

# --- 6. API key check ---------------------------------------------------------
log "Checking API key discovery..."
KEY_STATUS="missing"
KEY_SOURCE=""

if [[ -n "${DEHASHED_API_KEY:-}" ]]; then
  KEY_STATUS="ok"
  KEY_SOURCE="DEHASHED_API_KEY env var"
else
  for pattern in \
    "$HOME/git/DeHashed-API-Tool/dehashapitool/config.txt" \
    "$HOME/dev/DeHashed-API-Tool/dehashapitool/config.txt" \
    "$HOME/code/DeHashed-API-Tool/dehashapitool/config.txt"; do
    if [[ -f "$pattern" ]]; then
      first_line=$(head -n 1 "$pattern" | tr -d '[:space:]')
      if [[ -n "$first_line" && "$first_line" != "<api-key>" ]]; then
        KEY_STATUS="ok"
        KEY_SOURCE="$pattern"
        break
      fi
    fi
  done
  if [[ "$KEY_STATUS" != "ok" ]]; then
    for glob in "$HOME"/.local/pipx/venvs/dehashapitool/lib/python*/site-packages/dehashapitool/config.txt \
                "$HOME"/.local/share/pipx/venvs/dehashapitool/lib/python*/site-packages/dehashapitool/config.txt; do
      for p in $glob; do
        [[ -f "$p" ]] || continue
        first_line=$(head -n 1 "$p" | tr -d '[:space:]')
        if [[ -n "$first_line" && "$first_line" != "<api-key>" ]]; then
          KEY_STATUS="ok"
          KEY_SOURCE="$p"
          break 2
        fi
      done
    done
  fi
fi

echo
if [[ "$KEY_STATUS" == "ok" ]]; then
  ok "API key found via: $KEY_SOURCE"
else
  warn "No API key found. Before the skill can make live calls, do one of:"
  warn "  export DEHASHED_API_KEY='your-key'    # shell profile"
  warn "  dat --store-key                       # if dehashapitool CLI is installed"
fi

echo
ok "Install complete."
echo "    Skill:     $SKILL_TARGET"
echo "    Command:   $CMD_TARGET"
echo "    Try it:    type  /dehashed  inside Claude Code"
