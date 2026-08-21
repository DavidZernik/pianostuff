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

# Each mix is levelled to the same loudness. Without this the isolated vocal sits
# 8.6 dB below the full song, so at one slider position the full song is fine and
# "vocals only" sounds like nothing is playing at all — which is exactly how it was
# reported. A limiter catches the peaks on the mixes that are already near full
# scale rather than letting them clip.
TARGET=-20

mix() {  # mix <out> <stem>...
  local out=$1; shift
  local -a args=() ; local fc="" tags="" i=0
  for s in "$@"; do
    args+=(-t "$D" -i "$S/$s.mp3")
    fc+="[$i:a]atrim=0:$D[s$i];"
    tags+="[s$i]"
    i=$((i+1))
  done
  local tmp="player/.$out"
  ffmpeg -v error -y "${args[@]}" \
         -filter_complex "${fc}${tags}amix=inputs=$i:normalize=0[m]" \
         -map "[m]" -c:a libmp3lame -q:a 4 "$tmp"
  level "$tmp" "$out"
}

level() {  # level <infile> <outname> — bring to TARGET and limit the peaks
  local tmp=$1 out=$2
  local mean gain
  mean=$(ffmpeg -hide_banner -i "$tmp" -af volumedetect -f null - 2>&1 \
         | sed -n 's/.*mean_volume: \(.*\) dB/\1/p')
  gain=$(python3 -c "print(f'{$TARGET - ($mean):.1f}')")
  ffmpeg -v error -y -i "$tmp" -af "volume=${gain}dB,alimiter=limit=0.89" \
         -c:a libmp3lame -q:a 4 "player/$out"
  rm -f "$tmp"
  printf "  %-24s %6.1f s  %+5s dB\n" "$out" \
    "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "player/$out")" "$gain"
}

# Six mixes, built from three parts you can name: vocals, bass, keyboard. Drums go
# in the two you play along to and stay out of the ones you study with.
mix vocals.mp3            "0 Lead Vocals" "1 Backing Vocals"
mix bass.mp3              "3 Bass"
mix bass-drums.mp3        "3 Bass" "2 Drums" "5 Percussion"
mix vocals-bass-drums.mp3 "0 Lead Vocals" "1 Backing Vocals" "3 Bass" "2 Drums" "5 Percussion"
mix keys-bass-vocals.mp3  "4 Keyboard" "3 Bass" "0 Lead Vocals" "1 Backing Vocals"
# The band with both your jobs removed: no keyboard to fight the part you are playing,
# no vocal to sing over you. Synth, Other and Brass stay — they carry the horn stabs and
# the layer that takes the solo at bar 88, which are not the piano part.
mix band.mp3              "2 Drums" "3 Bass" "5 Percussion" "6 Synth" "7 Other" "8 Brass"
ffmpeg -v error -y -i "audio/One Page A Week copy.mp3" -t "$D" -c:a libmp3lame -q:a 4 player/.song.mp3
level player/.song.mp3 song.mp3
rm -f player/bed.mp3 player/band-minus-piano.mp3 player/keys-drums.mp3 player/vocals-keys.mp3 player/keys.mp3
echo "  removed the old mixes"
