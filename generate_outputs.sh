#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Config (defaults) — edit these or override via flags below
# ============================================================
# KiCad bin folder. On most Linux distros, kicad-cli is in /usr/bin.
# If you use Flatpak or a custom install, point to its bin:
#   Flatpak example:
#   KICAD_BIN="/var/lib/flatpak/app/org.kicad.KiCad/current/active/files/bin"
KICAD_BIN="/usr/bin"

# Project *stem* (without extension), relative to repo root (this script's dir)
PROJECT_DEFAULT="CAD/<proj_name>/<proj_name>"

# Vendor for KiKit fab (e.g., jlcpcb, pcbway). Leave empty to skip KiKit.
VENDOR_DEFAULT="jlcpcb"

# Base options for build_outputs.py
BASE_OPTS=(--no-timestamp --iso --zip)
# ============================================================

# --- Helpers ---
die() { printf "ERROR: %s\n" "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# Always run from the script's directory (repo root)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Parse flags: -p/--project, -v/--vendor, -- (pass-thru to Python)
PROJECT="$PROJECT_DEFAULT"
VENDOR="$VENDOR_DEFAULT"
EXTRA_OPTS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--project) PROJECT="${2:?missing value for --project}"; shift 2;;
    -v|--vendor)  VENDOR="${2:?missing value for --vendor}"; shift 2;;
    -h|--help)
      cat <<EOF
Usage: $0 [options] [-- extra-python-options]

Options:
  -p, --project  Path (stem) to .kicad_pro without extension
                 (default: $PROJECT_DEFAULT)
  -v, --vendor   KiKit vendor (e.g., jlcpcb). Empty to skip KiKit
                 (default: $VENDOR_DEFAULT)
  -h, --help     Show this help

Examples:
  $0
  $0 -v pcbway
  $0 -p CAD/other/board -v "" -- --glb  # skip KiKit; add --glb to Python
EOF
      exit 0
      ;;
    --) shift; EXTRA_OPTS=("$@"); break;;
    *)  EXTRA_OPTS+=("$1"); shift;;
  esac
done

# PATH: ensure KiCad bin is visible (so kicad-cli is found by your Python script)
export PATH="$KICAD_BIN:$PATH"

# Sanity checks
have python3 || die "python3 not found. Install Python 3."
have kicad-cli || echo "WARN: kicad-cli not found on PATH. If KiCad is installed elsewhere, set KICAD_BIN at top of this script."

# Build options for Python
OPTS=("${BASE_OPTS[@]}")
if [[ -n "$VENDOR" ]]; then
  OPTS+=(--kikit "$VENDOR")
fi
# Allow additional flags after --
OPTS+=("${EXTRA_OPTS[@]}")

echo "Generating outputs for \"$PROJECT\" with vendor \"${VENDOR:-<none>}\""
python3 "$ROOT/build_outputs.py" --project "$PROJECT.kicad_pro" "${OPTS[@]}"

echo "Done."
