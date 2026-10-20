#!/usr/bin/env bash
# Fetches the sources references/circuits/*.md were written from into references/circuits/sources/ and checks each is the copy
# it was read from (sha256, 2026-10-18 / 2026-10-19; the Buchla 259 and 292 sources moved here from 2sl gate 2026-10-20; the Moog ladder's 2026-10-20). Nothing fetched is kept in git (.gitignore).
# Fails loudly, naming the file, when a download fails or a file changed upstream.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out_dir="$here/sources"
mkdir -p "$out_dir"
# The Buchla schematic scans are Magnus Danielson's (rubidium.dyndns.org, now offline), served raw by the Wayback Machine.
magnus="rubidium.dyndns.org/~magnus/synths/companies/buchla"
wayback="https://web.archive.org/web"
aalto="https://research.spa.aalto.fi/publications/papers/dafx13-lpg"
ported="https://raw.githubusercontent.com/madskjeldgaard/portedplugins/c6c0d7430e9bc8e8aaeae3db8263e1dbb8f398eb/plugins"
# name | url | sha256
sources=(
  "ltc1060-1060fb.pdf|https://www.komponenten.es.aau.dk/fileadmin/komponenten/Data_Sheet/Switch_Cap/LTC1060.pdf|4114b99dbe5fef8ed1ef7520f69f27209bbbf7cae50a88ef507bd95fb960bf25"
  "mf10-n.pdf|https://www.ti.com/lit/ds/symlink/mf10-n.pdf|0e837564aa0bc5e6b3f78bd95e3fa45b0bf7c8554989e4f76d9d86b3c876079d"
  # buchla-259.md
  "Buchla_2590_1_200.jpg|$wayback/20190514160939id_/https://$magnus/Buchla_2590_1_200.jpg|29c9abed63fec0fa73b8ea18af5bd736598b34ad4fd385813a2760050a3f7aa7"
  "Buchla_2590_2_200.jpg|$wayback/20160913101657id_/http://$magnus/Buchla_2590_2_200.jpg|a860d85d0b6666d200dce2a66c8cd1c22473e7f7e6aaf712c096a109f0ba997f"
  "Buchla_2590_3_200.jpg|$wayback/20160913160041id_/http://$magnus/Buchla_2590_3_200.jpg|1143965e8620974380633c8a611114403cf99830d54c681f6906c54f898c762d"
  "Buchla_2590_4_200.jpg|$wayback/20160913095455id_/http://$magnus/Buchla_2590_4_200.jpg|de8d06491e2b2d82c03bcaeabba1489073ec0ffcfef6167bd7569f665c291bc1"
  "Buchla_2920B_200.jpg|$wayback/20160913104217id_/http://$magnus/Buchla_2920B_200.jpg|f0c0815e6c229179581615c446ac59769e4faa35382cb214851fc7557e1958a6"
  "Buchla_2920C_200.jpg|$wayback/20160913095818id_/http://$magnus/Buchla_2920C_200.jpg|318cf529be2df37bb3b2c543392c41d4ae52828683e22fdcc5205f9b768ac330"
  "theelen-259timbre-v05.pdf|https://www.ecalpemos.nl/wp-content/uploads/259timbre_mod-index_schematics-v05.pdf|393e2127da068d83591f7f2e0928c8ae9822a8dcb25f0b9dadd36c85af51722a"
  "esqueda-et-al-dafx17.pdf|https://www.dafx.de/paper-archive/2017/papers/DAFx17_paper_82.pdf|1dc7ef713521ed850d1c5a1b2511c98168f761aa1a7fe4a10dd3e0f25d1faf8d"
  "CA3160-intersil-FN976.4.pdf|https://gia.iqm.unicamp.br/datasheet/CA3160.pdf|28ac23ac0a1cb8374486d217ac05c25087eba383c6fafb4c3e3a76970bee9f97"
  "tl072-ti-SLOS080W.pdf|https://www.ti.com/lit/ds/symlink/tl072.pdf|13366ea85bacfe27406b66acc57e9163a5e4bc5138c319591f19dbe957fdc54f"
  "1n5221-vishay.pdf|https://www.vishay.com/docs/85588/1n5221.pdf|10af8e5f252fc19d2a6bf68c0e3c33632e65ca4cc6f5b7969d967313c326c32f"
  "tiptop-259t-manual.pdf|https://tiptopaudio.com/manuals/Buchla_&_Tiptop_Audio_259t.pdf|651b1f0dba69959d41e9dea048693c8c6792f4721cab3770dd7445d6996827b1"
  # buchla-292-low-pass-gate.md
  "parker-dangelo-dafx13.pdf|https://www.dafx.de/paper-archive/2013/papers/44.dafx2013_submission_56.pdf|7d0192860e729e6afa0b08b90494c5d849ed0d3a32903f1f5b07941c423f8fcf"
  "parker-dangelo-dafx13-authors-site.pdf|$aalto/DAFx2013-LPG.pdf|a4d3865b66e189435226e4f22472463237fefc45940b73a52cbe8915df639013"
  "LPG_demo.maxpat|$aalto/source/LPG_demo.maxpat|cb3d5d22dd1d28e85167047531b47e9d8516f497bb3ca1da97e62f736e52c651"
  "LPG_nonlin.gendsp|$aalto/source/LPG_nonlin.gendsp|bd98f0add9e2158d62c1307e6987e6360b7e25b4025b085ae1d15ce8abdfe0c2"
  "poly_lpg.maxpat|$aalto/source/poly_lpg.maxpat|03b144244dc85061f5744cf3f39444be0f1f127a7e42658688e536751c192770"
  "LPG_both_square.aif|$aalto/LPG_both_square.aif|2c0c6cb4f89b576503bc80e75d8577064df28266879da7d5e3afbbc36763e7fc"
  "LPG_both_FM.aif|$aalto/LPG_both_FM.aif|918ab1ae3a95db1d6ac95835a299b6a888fb3a6b2abbd43ca5ad81fbbde7d688"
  "LPG_both_noise.aif|$aalto/LPG_both_noise.aif|946f48a82da61e0d7480247c8e9fbc523f2466e65c95a6b7b5d155cf5bc3bf66"
  "LPG_LP_FM.aif|$aalto/LPG_LP_FM.aif|bfb4e0cddc4d7758eb8200283be98f15b57ff46a66bfc24e3b01428ada15e12f"
  "najnudel-et-al-dafx23.pdf|https://www.dafx.de/paper-archive/2023/DAFx23_paper_50.pdf|1a715de02fabb617c00d303d01d6dff91adeca4a429c4573873aaeed2dd36037"
  "vtl5c3-akizuki.pdf|https://akizukidenshi.com/goodsaffix/vtl5c3.pdf|5081cc7bbccc01e26c0c0439ef4261c9635cebe23598a01386bdbcb880189874"
  "perkinelmer-vt500-catalog.pdf|https://www.amstzone.org/PerkinElmer-VT500.pdf|f932833fc7ce96715803e79edc0c0393ce307704edab08b0457e0f05ae6594fd"
  "portedplugins-lpg.cpp|$ported/lpg.cpp|a1d5b4860925da6eb9a7eacfcd6225a8cd3596906a7c5eeb5e77990d6686bcd0"
  "portedplugins-lpg.hpp|$ported/lpg.hpp|3cedceb43c3f0fa0e305f6298eda53e20e431a94882752d7e980dc92ec4dbbf0"
  "portedplugins-LPG.cpp|$ported/LPG/LPG.cpp|49955094b2e8b4843a85870e778483f1510f768a7b1e09867e0a59b9bc4c139a"
  "portedplugins-LPG.hpp|$ported/LPG/LPG.hpp|e2b09c27966c28cadff20557c0b541cc768dda3676ab07a9a9fb80faca980128"
  # moog-transistor-ladder.md (2026-10-20)
  "moog-patent-us3475623.pdf|https://patentimages.storage.googleapis.com/ea/a3/6e/d3c9ff36d3e14a/US3475623.pdf|464ba3222f40e8430281388b06085177702331b2d87c9ec9361c929f48480905"
  "minimoog-vcf-schematic.gif|http://www.fantasyjackpalance.com/fjp/sound/synth/synthdata/16-minimoog/001/911-filt-print-circ-schem.gif|ea509b37b3a6aa3a9af9ca7bd7a774483cd48f0565a6219399ce851c125984c1"
  "moog-904a-schematic.jpg|$wayback/20070623230759id_/http://www.hylander.com/images/schematics/904a.jpg|63a56d80d69a7cf429e0804b0aadb17d4b181075b325a6e6ead36373f74a2855"
  "stinchcombe-moog-ladder-tf.pdf|https://www.timstinchcombe.co.uk/synth/Moog_ladder_tf.pdf|34d93147b915db0e5d757d3dd3b4888e986f5fa345c56ed110e22c7dd1e9fd78"
  "huovilainen-dafx04.pdf|https://dafx.de/paper-archive/2004/P_061.PDF|d8bee4101c859f3eb8f0ccc0d08d6a3af09745ccce4c6549e46dd27138a30d67"
  "stilson-smith-icmc1996.pdf|https://ccrma.stanford.edu/~stilti/papers/moogvcf.pdf|0253df9ebf59b4bbafd167b3ce9a96397acf37c0b335ea4b8f9f82cb0ebea46d"
  "dangelo-valimaki-generalized-moog-part1-taslp2014.pdf|https://aaltodoc.aalto.fi/server/api/core/bitstreams/7ebb6719-8c32-4e23-97ce-b6ebac589990/content|8f485ee1ee77e80566cf6570573043a53ef96ae4a20eff8574c4748126b9b91c"
  "dangelo-dissertation-aalto-2014.pdf|https://aaltodoc.aalto.fi/server/api/core/bitstreams/f87d5b89-72b1-4b8a-85bd-e8ef9511937d/content|9bf563a5491dcea47342ebfd3d7deacbee16977035c2c52fe62e6a00de012013"
)
failed=0
for entry in "${sources[@]}"; do
  IFS='|' read -r name url expected_sha256 <<< "$entry"
  target="$out_dir/$name"
  if ! curl -fsSL -A "Mozilla/5.0" -o "$target" "$url"; then
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
