#!/bin/zsh
# Copies the terms and privacy policy from the app (the source) to the website, so both show the
# same text. Run from anywhere after editing all-mo-diary-app/assets/texts/*.md.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for doc in terms privacy; do
  cp "$ROOT/all-mo-diary-app/assets/texts/$doc.md" "$ROOT/all-mo-diary-web/legal/$doc.md"
  echo "copied $doc.md"
done
