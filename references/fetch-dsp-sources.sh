#!/usr/bin/env bash
# Fetches the sources references/dsp.md was written from into references/dsp-sources/ and checks each is the copy
# it was read from (sha256, 2026-10-18 / 2026-10-19 / 2026-10-20 / 2026-10-21). Nothing fetched is kept in git (.gitignore).
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
  "microtonic-user-guide-3.3.4.pdf|https://soniccharge.com/public/Microtonic%20User%20Guide.pdf|511c69d53991288431eb890e8ee80f7a5c44f513f4a6a876f718f78d41fcfb94"
  "park-miller-cacm1988.pdf|https://www.firstpr.com.au/dsp/rand31/p1192-park.pdf|69b0a6f2df4a794b982de14e3af12d97047668ee5e11dd098a6bacb6f85c28f6"
  "jomox-mbase11-manual.pdf|https://www.jomox.de/upload/manuals/MBase11_E.pdf|10350e766ff794a6afca61b268d8aea2e094cbe8d595aebeb0449c81240b0ef0"
  # the spring tanks (2026-10-21)
  "parker-bilbao-dafx09.pdf|https://www.dafx.de/paper-archive/2009/papers/paper_84.pdf|db1a09541d7e0579238c60bb2c668d6638f1a92172ce3e7b3f565fd855655885"
  "parker-eurasip2011.pdf|https://acris.aalto.fi/ws/portalfiles/portal/13004391/art_10.1155_2011_646134.pdf|ffdb0ddc74ae9b7e7352ad8698f2d0fc7c0c18b4654a14e93b5bcc39d014b9fe"
  "gamper-parker-valimaki-dafx11.pdf|https://www.dafx.de/paper-archive/2011/Papers/39_e.pdf|1a5f630165a7ab302998abb5c66dcc05fffbb4acd6c9305344feabe5bec92fbb"
  "lapastina-dangelo-gabrielli-dafx21.pdf|https://www.dafx.de/paper-archive/2021/proceedings/papers/DAFx20in21_paper_27.pdf|2673492050d120d39962d65805764fa2368dc0bc614930e15c8bb93cc971b7bc"
  "hiir-1.40.zip|https://ldesoras.fr/src/hiir-1.40.zip|ed1d630f85b4ed1eeda8de16acb1f785b18fc93d1430c1956192c6cc1df4221e"
  "raffel-smith-bbd-dafx10.pdf|https://dafx.de/paper-archive/2010/DAFx10/RaffelSmith_DAFx10_P42.pdf|0187a788d0ac89dc42302c4785c1c6ae682e1ac325c6d42d6241766018142538"
  "holters-parker-bbd-dafx18.pdf|https://dafx.de/paper-archive/2018/papers/DAFx2018_paper_12.pdf|29e6b14b25b29bdde1c0368d5a856c77118454c53adb63436613129c371e6e73"
  "cycling74-gen-workshop-grranulator.genexpr|https://raw.githubusercontent.com/Cycling74/gen-workshop/f114ce93744687fc9724543e8c20c0baeed58221/patchers/grranulator.genexpr|c894ca0f904781d9a129a0874cb4c0bffc1d72e3fde7eea77e6723d92d496c54"
  "pdmeyer-voice_allocator.genexpr|https://raw.githubusercontent.com/pdmeyer/philip-meyer-max-tutorials/d1f54136829804f16587ddefed0567459bfbaa49/patchers/signal-polyphony/signal-polyphony/other/voice_allocator.genexpr|936ccb9f878df1ff16a31d5eeb20419ea42aa6ffddd4122bc8b3c61d7951d14c"
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
