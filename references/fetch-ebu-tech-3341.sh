#!/usr/bin/env bash
# Fetches EBU Tech 3341 (V4, November 2023), "Loudness Metering: 'EBU Mode' metering to supplement EBU R 128 loudness
# normalization": the momentary loudness and its maximum, and checks it is the copy ebu-tech-3341.md was read from.
# The PDF is not kept in git.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
url='https://tech.ebu.ch/docs/tech/tech3341.pdf'
expected_sha256="dd5a7b0b611024e616b86a42c89eed0ded33f3129afc1994204885216fa1619e"
out="$here/ebu-tech-3341.pdf"
curl -fsSL -o "$out" "$url"
actual_sha256="$(sha256sum "$out" | cut -d' ' -f1)"
if [ "$actual_sha256" != "$expected_sha256" ]; then
  echo "ebu-tech-3341.pdf changed upstream: sha256 $actual_sha256, read from $expected_sha256" >&2
  exit 1
fi
echo "fetched $out"
