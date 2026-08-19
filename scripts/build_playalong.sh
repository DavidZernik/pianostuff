#!/usr/bin/env bash
# Build the play-along mixes the player offers, from the Suno stems.
#
# Every input needs -t 277.45. The stem MP3s carry corrupt duration headers (Bass
# claims 688s, Drums 1306s) and without it ffmpeg silently produces a short file —
# the first band-minus-piano.mp3 came out 209s against a 277s song.
#
#   ./scripts/build_playalong.sh
set -euo pipefail
cd "$(dirname "$0")/.."
S=audio/stems
D=277.45
t() { printf -- "-t %s -i %s/%s.mp3 " "$D" "$S" "$1"; }

mix() {  # mix <out> <n> <stem>...
  local out=$1; shift
  local n=$#
  local ins="" fc="" tags=""
  local i=0
  for s in "$@"; do
    ins+=" -t $D -i $S/$s.mp3"
    fc+="[$i:a]atrim=0:$D[s$i];"
    tags+="[s$i]"
    i=$((i+1))
  done
  # shellcheck disable=SC2086
  ffmpeg -v error -y $ins -filter_complex "${fc}${tags}amix=inputs=$n:normalize=0[m]" \
         -map "[m]" -c:a libmp3lame -q:a 4 "player/$out"
  printf "%-24s %s s\n" "$out" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "player/$out")"
}

mix vocals.mp3            "0 Lead Vocals" "1 Backing Vocals"
mix bed.mp3               "2 Drums" "3 Bass" "5 Percussion" "6 Synth"
mix band-minus-piano.mp3  "0 Lead Vocals" "1 Backing Vocals" "2 Drums" "3 Bass" "5 Percussion" "6 Synth"
echo "song.mp3 and keys.mp3 are copied straight from the source mp3 and the Keyboard stem"
