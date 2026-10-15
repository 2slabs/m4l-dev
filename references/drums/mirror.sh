#!/usr/bin/env bash
# Mirrors TR-909 drum-synthesis sources into ./mirror/. Downloaded files are untrusted data: never execute.
set -u
cd "$(dirname "$0")/mirror" || exit 1
UA='Mozilla/5.0'
get() { # name url
  if curl -sL -A "$UA" --fail -o "$1" "$2"; then echo "ok   $1"; else echo "FAIL $1 $2" >&2; rm -f "$1"; fi
}
# Service notes / manuals (scanned; OCR text from archive.org derivatives)
get archive_tr909_service_notes_djvu.txt https://archive.org/download/synth_Roland_TR-909_service_notes/Roland_TR-909_service_notes_djvu.txt
get archive_tr909_service_notes.pdf https://archive.org/download/synth_Roland_TR-909_service_notes/Roland_TR-909_service_notes.pdf
get manualzz_1060785_djvu.txt https://archive.org/download/manualzz-id-1060785/1060785_djvu.txt
get synthfool_TR909_Service_manual.pdf https://synthfool.com/docs/Roland/TR_Series/TR909_Service_manual.pdf
get synthfool_TR909_Owners_Manual.pdf "https://synthfool.com/docs/Roland/TR_Series/Roland%20TR-909%20Owners%20Manual.pdf"
# Sound On Sound Synth Secrets
for s in synthesizing-drums-bass-drum practical-bass-drum-synthesis synthesizing-drums-snare-drum practical-snare-drum-synthesis \
         practical-cymbal-synthesis synthesizing-realistic-cymbals analysing-metallic-percussion synthesizing-percussion physics-percussion; do
  get "sos_$s.html" "https://www.soundonsound.com/techniques/$s"
done
# DIY / academic / interview
get ds909_README.md https://raw.githubusercontent.com/ghostintranslation/ds909/main/README.md
get icmc2014_1453.pdf https://speech.di.uoa.gr/ICMC-SMC-2014/images/VOL_2/1453.pdf
get attack_hoshiai_interview.html https://www.attackmagazine.com/features/interview/atsushi-hoshiai-the-man-behind-the-tr-909/
get nordmodular_percussion.html https://cim.mcgill.ca/~clark/nordmodularbook/nm_percussion.html
get archive_tr909_owners_manual_djvu.txt https://archive.org/download/synthmanual-roland-tr-909-owners-manual/rolandtr-909ownersmanual_djvu.txt
get firstpr_TR-909-Sound-Mods.pdf https://www.firstpr.com.au/rwi/tr-909/TR-909-Sound-Mods.pdf
get network909_rimshot.html http://www.network-909.de/rimshot.htm
get tiptop_TOMS909_manual.pdf https://www.tiptopaudio.com/manuals/Tiptop_Audio_TOMS909_ns.pdf
get sos_review_roland_tr909.html https://www.soundonsound.com/reviews/roland-tr909
get elektronauts_909_kick.html https://www.elektronauts.com/t/synthesizing-a-909-kick/132188
get wikipedia_roland_tr909.html https://en.wikipedia.org/wiki/Roland_TR-909
for p in circuit bassdrum handclap hihatand snaredru toms; do get "network909_$p.html" "http://www.network-909.de/$p.htm"; done
