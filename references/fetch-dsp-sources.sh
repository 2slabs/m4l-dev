#!/usr/bin/env bash
# Fetches the sources references/dsp.md was written from into references/dsp-sources/ and checks each is the copy
# it was read from (sha256, 2026-10-18 / 2026-10-19 / 2026-10-20). Nothing fetched is kept in git (.gitignore).
# Fails loudly, naming the file, when a download fails or a file changed upstream.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out_dir="$here/dsp-sources"
mkdir -p "$out_dir"
# name | url | sha256
sources=(
  "zavalishin-va-filter-design-2.1.2.pdf|https://web.archive.org/web/2023if_/https://www.native-instruments.com/fileadmin/ni_media/downloads/pdf/VAFilterDesign_2.1.2.pdf|a9e82cd6280284ff11c4badbdf22576c9015deab02975c72cea91bdc00846043"
  "bilbao-adaa-spl2017.pdf|https://aaltodoc.aalto.fi/bitstreams/e4bf0f6f-cf73-4311-bd9f-69c0f484064d/download|5b54566c3b4deb19cdad745c743eaf5b4d15b06d7ad86bfaf229123db85a7f23"
  "parker-zavalishin-lebivic-dafx16.pdf|https://www.dafx.de/paper-archive/2016/dafxpapers/20-DAFx-16_paper_41-PN.pdf|d23eee1d25574a1693928b03216b537c576b54cc57e0d021144a67f04bafec73"
  "esqueda-blamp-dafx16.pdf|https://www.dafx.de/paper-archive/2016/dafxpapers/18-DAFx-16_paper_33-PN.pdf|7ece0726a09efa5d3b8678d9507c2217d99c097e79fcaafe6f8cf03a9af9d663"
  "valimaki-polyblep-jasa2012.pdf|https://mac.kaist.ac.kr/pubs/ValimakiPeknenNam-jasa2012.pdf|a7b4d96daa8fbd53071549040cc59d0665dcd21cd3cb70d9581b9fd60ad03f13"
  "downing-terjesen-re201-2016.pdf|https://hajim.rochester.edu/ece/sites/zduan/teaching/ece472/projects/2016/Downing_Terjesen_paper.pdf|c0e25607c04b99d36e0a0489d45df420d4cf86559937ed013540020bc0eceae8"
  "chowdhury-tape-dafx19.pdf|https://dafx.de/paper-archive/2019/DAFx2019_paper_3.pdf|a915d63daee36556a4f267d9a52f07b1000988ecb48013589d926951a10d613c"
  "jos-thiran-allpass.html|https://ccrma.stanford.edu/~jos/pasp/Thiran_Allpass_Interpolators.html|64f53c6e54181a8dbcdaff858df22e18ea045b9f25ed6dd9ab2373f605cd560c"
  "parker-dangelo-dafx13.pdf|https://www.dafx.de/paper-archive/2013/papers/44.dafx2013_submission_56.pdf|7d0192860e729e6afa0b08b90494c5d849ed0d3a32903f1f5b07941c423f8fcf"
  "najnudel-et-al-dafx23.pdf|https://www.dafx.de/paper-archive/2023/DAFx23_paper_50.pdf|1a715de02fabb617c00d303d01d6dff91adeca4a429c4573873aaeed2dd36037"
  "perkinelmer-vt500-catalog.pdf|https://www.amstzone.org/PerkinElmer-VT500.pdf|f932833fc7ce96715803e79edc0c0393ce307704edab08b0457e0f05ae6594fd"
  "data-knot-dk_reverb_library.genexpr|https://raw.githubusercontent.com/rconstanzo/data-knot/e8ebcecadbf0cade540093ab80d0ea726f325f5f/code/dk_reverb_library.genexpr|208e707616dba19ad5c326497c288d8039ba95b30964eafbc546bbdf4fbf36b4"
)
failed=0
for entry in "${sources[@]}"; do
  IFS='|' read -r name url expected_sha256 <<< "$entry"
  target="$out_dir/$name"
  if ! curl -fsSL -o "$target" "$url"; then
    echo "FAILED to download $name from $url" >&2
    failed=1
    continue
  fi
  actual_sha256="$(sha256sum "$target" | cut -d' ' -f1)"
  if [ "$actual_sha256" != "$expected_sha256" ]; then
    echo "CHANGED: $name ($url) has sha256 $actual_sha256, the notes were written from $expected_sha256" >&2
    failed=1
  else
    echo "ok $name"
  fi
done
exit "$failed"
