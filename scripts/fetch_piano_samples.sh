#!/usr/bin/env bash
# Salamander Grand Piano (Yamaha C5) by Alexander Holm — CC-BY 3.0
# Sampled every 3 semitones; the player pitch-shifts to fill the gaps.
set -e
cd "$(dirname "$0")/../player" && mkdir -p piano && cd piano
for n in C1 Ds1 Fs1 A1 C2 Ds2 Fs2 A2 C3 Ds3 Fs3 A3 C4 Ds4 Fs4 A4 C5 Ds5 Fs5 A5 C6 Ds6 Fs6 A6 C7; do
  [ -f "$n.mp3" ] || curl -sS --retry 2 --max-time 30 -o "$n.mp3" \
     "https://tonejs.github.io/audio/salamander/$n.mp3"
done
echo "$(ls -1 *.mp3 | wc -l | tr -d ' ') samples in $(pwd)"
