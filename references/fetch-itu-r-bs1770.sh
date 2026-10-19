#!/usr/bin/env bash
# Fetches Recommendation ITU-R BS.1770-5 (11/2023), the loudness and true-peak algorithms, and checks it is the copy
# itu-r-bs1770.md was transcribed from. The PDF is not kept in git.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
url='https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf'
expected_sha256="eefb926f72f72a96b96f251067bfee0650a0f29a26f60661d354162038b041ad"
out="$here/itu-r-bs1770-5.pdf"
curl -fsSL -o "$out" "$url"
actual_sha256="$(sha256sum "$out" | cut -d' ' -f1)"
if [ "$actual_sha256" != "$expected_sha256" ]; then
  echo "itu-r-bs1770-5.pdf changed upstream: sha256 $actual_sha256, transcribed from $expected_sha256" >&2
  exit 1
fi
echo "fetched $out"
