#!/usr/bin/env bash
# Pitch-shift every play-along mix down for the transposed key.
#
# This ffmpeg has no rubberband, so the shift is resample-then-restore-tempo:
# asetrate drops pitch and speed together, atempo puts the speed back. For three
# semitones that is a 12% stretch, which atempo handles without obvious artifacts.
# Anything much larger would want a real phase vocoder.
#
#   ./scripts/build_transposed_playalong.sh [semitones_down]      (default 3)
set -euo pipefail
cd "$(dirname "$0")/.."
N=${1:-3}
SUF=Em
R=$(python3 -c "print(f'{2**(-$N/12):.9f}')")     # pitch ratio, <1 = lower
T=$(python3 -c "print(f'{2**($N/12):.9f}')")      # tempo correction, the inverse
echo "down $N semitones — pitch x$R, tempo x$T"
for f in vocals bass bass-drums vocals-bass-drums keys-bass-vocals band song; do
  [ -f "player/$f.mp3" ] || continue
  SR=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of csv=p=0 "player/$f.mp3")
  ffmpeg -v error -y -i "player/$f.mp3" \
         -af "asetrate=${SR}*${R},atempo=${T},aresample=${SR}" \
         -c:a libmp3lame -q:a 4 "player/$f-$SUF.mp3"
  printf "  %-24s %6.1f s\n" "$f-$SUF.mp3" \
    "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "player/$f-$SUF.mp3")"
done
