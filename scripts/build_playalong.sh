#!/usr/bin/env bash
# Build the play-along mixes the player offers, from the Suno stems.
#
# Every input needs -t 277.45. The stem MP3s carry corrupt duration headers (Bass
# claims 688s, Drums 1306s) and without it ffmpeg silently produces a short file —
# the first band-minus-piano.mp3 came out 209s against a 277s song.
#
# Stem filenames contain spaces, so the ffmpeg arguments are built as an array.
# Word-splitting a flat string here silently looks for a stem called "0".
#
#   ./scripts/build_playalong.sh
set -euo pipefail
cd "$(dirname "$0")/.."
S=audio/stems
D=277.45

mix() {  # mix <out> <stem>...
  local out=$1; shift
  local -a args=() ; local fc="" tags="" i=0
  for s in "$@"; do
    args+=(-t "$D" -i "$S/$s.mp3")
    fc+="[$i:a]atrim=0:$D[s$i];"
    tags+="[s$i]"
    i=$((i+1))
  done
  ffmpeg -v error -y "${args[@]}" \
         -filter_complex "${fc}${tags}amix=inputs=$i:normalize=0[m]" \
         -map "[m]" -c:a libmp3lame -q:a 4 "player/$out"
  printf "  %-22s %6.1f s\n" "$out" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "player/$out")"
}

mix vocals.mp3            "0 Lead Vocals" "1 Backing Vocals"
mix bed.mp3               "2 Drums" "3 Bass" "5 Percussion" "6 Synth"
mix band-minus-piano.mp3  "0 Lead Vocals" "1 Backing Vocals" "2 Drums" "3 Bass" "5 Percussion" "6 Synth"
mix bass.mp3              "3 Bass"
mix keys-drums.mp3        "4 Keyboard" "2 Drums" "5 Percussion"
mix vocals-keys.mp3       "0 Lead Vocals" "1 Backing Vocals" "4 Keyboard"
echo "  song.mp3 and keys.mp3 come straight from the source mp3 and the Keyboard stem"
