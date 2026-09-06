#!/usr/bin/env bash
# One-shot onboarding setup for F.R.I.D.A.Y-AI (macOS / Linux / WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ""
echo "=== F.R.I.D.A.Y. setup ==="
echo "Repo root: $ROOT"
echo ""

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    echo "See SETUP.md prerequisites."
    exit 1
  }
}

need node
need npm

NODE_MAJOR="$(node -v | sed 's/^v//' | cut -d. -f1)"
if [ "$NODE_MAJOR" -lt 20 ]; then
  echo "Node $(node -v) detected — need Node 20+."
  exit 1
fi
echo "Node $(node -v) OK"

if [ -f .env.example ] && [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit LM_STUDIO_MODEL if needed."
elif [ -f .env ]; then
  echo ".env already present"
fi

echo ""
echo "Installing root dependencies (Husky / lint-staged)..."
npm install

echo ""
echo "Installing apps/web dependencies..."
(cd apps/web && npm install)

echo ""
echo "Ensuring git hooks..."
npx husky

cat <<'EOF'

=== Setup complete ===

Next (two terminals):

  1) Agent API (port 8090):
     ./scripts/run-agent-api.ps1   # or your local Python entry — see SETUP.md

  2) Web UI (port 5173):
     cd apps/web && npm run dev

Optional: start LM Studio local server on :1234 first.

Docs: SETUP.md · docs/CONTRIBUTING.md · docs/TROUBLESHOOTING.md

EOF
