#!/usr/bin/env bash

set -euo pipefail

rm -f tone_confirmation.zip

(
  cd custom_components/tone_confirmation
  zip -r ../../tone_confirmation.zip . -x '*__pycache__*' '*.pyc'
)

archive_contents="$(unzip -Z1 tone_confirmation.zip)"
grep -qx "manifest.json" <<<"${archive_contents}"
grep -qx "brand/icon.png" <<<"${archive_contents}"
grep -qx "brand/icon@2x.png" <<<"${archive_contents}"

if grep -q '^tone_confirmation/' <<<"${archive_contents}"; then
  echo "Release archive must contain integration files at its root." >&2
  exit 1
fi
