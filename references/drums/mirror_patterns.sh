#!/usr/bin/env bash
# Mirrors pattern-related sources into mirror/patterns/. Files are untrusted data; read with pdftotext / python3 -I only.
set -euo pipefail
dir="$(cd "$(dirname "$0")" && pwd)/mirror/patterns"
mkdir -p "$dir"
fetch() { # name url
  curl -fsSL -m 180 -A 'Mozilla/5.0' -o "$dir/$1" "$2" || { echo "FAILED: $2" >&2; exit 1; }
  echo "ok $1"
}
fetch tr909_owners_manual_ia.pdf "https://archive.org/download/synthmanual-roland-tr-909-owners-manual/$(curl -fsSL https://archive.org/metadata/synthmanual-roland-tr-909-owners-manual | python3 -I -c "import json,sys;print([f['name'] for f in json.load(sys.stdin)['files'] if f['name'].endswith('.pdf') and 'text' not in f['name']][0])")"
fetch tr909_owners_manual_ia_djvu.txt "https://archive.org/download/synthmanual-roland-tr-909-owners-manual/rolandtr-909ownersmanual_djvu.txt"
fetch euclidean_toussaint_banff.pdf "https://cgm.cs.mcgill.ca/~godfried/publications/banff.pdf"
fetch grids_pattern_generator.cc "https://raw.githubusercontent.com/pichenettes/eurorack/master/grids/pattern_generator.cc"
fetch grids_resources.cc "https://raw.githubusercontent.com/pichenettes/eurorack/master/grids/resources.cc"
fetch attack_basic_channel_dub_techno.html "https://www.attackmagazine.com/technique/beat-dissected/basic-channel-style-dub-techno/"
fetch attack_minimal_house.html "https://www.attackmagazine.com/technique/beat-dissected/minimal-house/"
fetch attack_detroit_techno.html "https://www.attackmagazine.com/technique/beat-dissected/motor-city-detroit-techno/"
fetch attack_deep_house.html "https://www.attackmagazine.com/technique/beat-dissected/deep-house-stripped-workout-beat-dissected/"
fetch ableton_live12_midi_tools.html "https://www.ableton.com/en/live-manual/12/midi-tools/"
fetch grids_docs.html "https://pichenettes.github.io/mutable-instruments-documentation/modules/grids/"
fetch elektron_digitakt_manual.pdf "https://www.elektron.se/wp-content/uploads/2026/10/Digitakt-User-Manual_ENG_OS1.54_260930.pdf"
fetch musicradar_jeff_mills_909.html "https://www.musicradar.com/how-to/how-to-program-jeff-mills-style-rolling-tr-909-drums"
fetch attack_dub_style_drum_processing.html "https://www.attackmagazine.com/technique/tutorials/dub-style-drum-processing-for-character-and-groove/"
fetch attack_dark_techno.html "https://attackmagazine.com/?p=71776"
fetch attack_rolling_techno.html "https://www.attackmagazine.com/technique/beat-dissected/rolling-techno/"
fetch attack_daw_drum_machine_swing.html "https://www.attackmagazine.com/technique/passing-notes/daw-drum-machine-swing/"
fetch studiobrootle_dub_techno_4_ingredients.html "https://www.studiobrootle.com/dub-techno-tutorial-4-ingredients/"
fetch studiobrootle_techno_drum_patterns.html "https://www.studiobrootle.com/techno-drum-patterns-and-drum-programming-tips/"
fetch beatkitchen_drum_programming.html "https://beatkitchen.io/guides/electronic-music/03-drum-programming/"
fetch elektronauts_drum_fills_8th_bar.html "https://www.elektronauts.com/t/drum-fills-on-8th-bar/193320"
