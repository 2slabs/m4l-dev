#!/usr/bin/env bash
# Fetches the sources references/circuits/mutron-bi-phase.md and references/allpass-and-diffusion.md were written from
# into references/phaser-diffusion-sources/ and checks each is the copy they were read from (sha256, 2026-10-20).
# Nothing fetched is kept in git (.gitignore). Fails loudly, naming the file, when a download fails or a file changed
# upstream. The Zavalishin PDF and the JOS Thiran page the allpass note also cites come from fetch-dsp-sources.sh.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out_dir="$here/phaser-diffusion-sources"
mkdir -p "$out_dir"
# name | url | sha256
sources=(
  "mutron-biphase-owners-manual.html|https://soundgas.com/resources/mutron-biphase-owners-manual|CONTAINS:two independent six-stage phase shifters"
  "arp-bi-phase-schematic-page1.gif|https://experimentalistsanonymous.com/diy/Schematics/Phasers/Mu-Tron%20Bi-phase%20page%201.gif|0500839f343d4236f4128686f29ad4a32f60c1e84db724cd22da2fa41ce7a27f"
  "arp-bi-phase-schematic-page2.gif|https://experimentalistsanonymous.com/diy/Schematics/Phasers/Mu-Tron%20Bi-phase%20page%202.gif|12d9ec8e13387d3d2950cc8e1448f84b9021fe68e841e75c3bbda8ea8ce0c528"
  "arp-bi-phase-schematic-page3-power.gif|https://experimentalistsanonymous.com/diy/Schematics/Phasers/Mu-Tron%20Bi-phase%20page%203.gif|d49cac1c9860a0051a239f7b8a715ea6e15518573a99f2564e0a0c4fc79c2de8"
  "diy-fet-bi-phaser-stage.gif|https://experimentalistsanonymous.com/diy/Schematics/Phasers/Mu-Tron%20Bi-Phase%20Phase%20Stage.gif|22f8f20d704e48d47ddcadeaf17775a4fc3b8a76a237805928e19e42ff2ff40e"
  "darabundit-univibe-dafx19.pdf|https://ccrma.stanford.edu/~champ/files/DAFx2019_paper_31.pdf|157b65bb558f59b062a08cefaee70013a3f32c34b8510972c728250327086c11"
  "geofex-phase-shifters.html|http://www.geofex.com/Article_Folders/phasers/phase.html|852d2881079a6b403899393767cf0de3b60002f7080718b5c6a2b87d916bc8ca"
  "moog-mf103-manual.pdf|https://www.fullcompass.com/common/files/86275-MF103SManual.pdf|7474802a747ccb3ca2067d6137e2e91ec97fccfe46e30eeaf961d9916b555e8a"
  "dattorro-effect-design-part1.pdf|https://ccrma.stanford.edu/~dattorro/EffectDesignPart1.pdf|23b630f7eb88c2922a7441dcdb74a9e91d9937c771d757dbc86259210bda39d1"
  "dattorro-effect-design-part2.pdf|https://ccrma.stanford.edu/~dattorro/EffectDesignPart2.pdf|fef75168d47bc85d0d92a853649828117459028c1fdcd70ec547509c4c643eb4"
  "valhalla-shimmer-notes.pdf|https://www.valhalladsp.com/shimmer/ValhallaShimmerNotes.pdf|6e53195263f45a59292c61c8d022b2a24bf0941208cee2076dc57aefb24825d0"
  "reason-building-shimmer-reverb.html|https://reasonstudios.com/news/post/building-shimmer-reverb|c2f54b8d97bf1dc3873a6780a63379fcbe84d9a78877465f3ac31fa3298cf338"
  "jos-allpass-filters.html|https://ccrma.stanford.edu/~jos/pasp/Allpass_Filters.html|d3a536274159b9713aa2c203c08b9e0ca0cb308dfff1fc134a367edb8c017871"
  "jos-allpass-two-combs.html|https://ccrma.stanford.edu/~jos/pasp/Allpass_Two_Combs.html|343ae0f39042dc749e833b269d9a58262240c6402fb351c0ed62f12226144a11"
  "jos-nested-allpass.html|https://ccrma.stanford.edu/~jos/pasp/Nested_Allpass_Filters.html|03e516f1c0cc2f2a1b8b8d34c1109dbccfc6757c86cc3158964f977a1bf49bb2"
  "jos-gerzon-nested-mimo-allpass.html|https://ccrma.stanford.edu/~jos/pasp/Gerzon_Nested_MIMO_Allpass.html|07de8d62c8fae862fa25f6d0bf396a3f1ca0400d06319e21c5b12bd4f5668e63"
  "jos-schroeder-allpass-sections.html|https://ccrma.stanford.edu/~jos/pasp/Schroeder_Allpass_Sections.html|9b26cf760997ffd60e3b0f13f775a3383a98ecf7da3532b421caf6c2b957b85e"
  "jos-schroeder-reverberators.html|https://ccrma.stanford.edu/~jos/pasp/Schroeder_Reverberators.html|2befa13f3a3d75d1212d2af16eff02d4c7f9e4d55a6a09e065e0b2f05028321f"
  "jos-freeverb.html|https://ccrma.stanford.edu/~jos/pasp/Freeverb.html|ace3270ffe37a01fca0ca1b251d53e2bce61f20b5bd8e7e3978d0093ad773ca5"
  "jos-freeverb-allpass-approximation.html|https://ccrma.stanford.edu/~jos/pasp/Freeverb_Allpass_Approximation.html|f2792223b4fc78dd39e8c8829b355c680106a92e98f33e487eb02c4b9f777611"
  "jos-phasing.html|https://ccrma.stanford.edu/~jos/pasp/Phasing.html|1f0ed6e979701df2fa20ad7c37dfa41a4f904a2ab3d11691d8e706c1179f1499"
  "jos-fractional-delay-filters.html|https://ccrma.stanford.edu/~jos/pasp/Fractional_Delay_Filters.html|2c761cbfb056f45772e588662b5ad089237c07a566f4a5e7f8175ec6e05bded8"
  "jos-lagrange-interpolation.html|https://ccrma.stanford.edu/~jos/pasp/Lagrange_Interpolation.html|3ecc9473e2ba0abd3918d0e09a6bdc8f819a4d4cb229185649430fd0fd365997"
)
failed=0
for entry in "${sources[@]}"; do
  IFS='|' read -r name url expected <<< "$entry"
  target="$out_dir/$name"
  if ! curl -fsSL -A "Mozilla/5.0" -o "$target" "$url"; then
    echo "FAILED to download $name from $url" >&2
    failed=1
    continue
  fi
  if [[ "$expected" == CONTAINS:* ]]; then
    phrase="${expected#CONTAINS:}"
    if grep -q -F "$phrase" "$target"; then echo "ok $name"; else
      echo "CHANGED: $name ($url) no longer contains: $phrase" >&2; failed=1; fi
    continue
  fi
  actual_sha256="$(sha256sum "$target" | cut -d' ' -f1)"
  if [ "$actual_sha256" != "$expected" ]; then
    echo "CHANGED: $name ($url) has sha256 $actual_sha256, the notes were written from $expected" >&2
    failed=1
  else
    echo "ok $name"
  fi
done
exit "$failed"
