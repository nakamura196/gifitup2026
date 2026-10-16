#!/usr/bin/env zsh
# encode frames -> final.gif (50 ms/frame) + contact strip of 8 frames
set -euo pipefail
D=$1; FPS=${FPS:-20}
ffmpeg -v error -y -framerate $FPS -i $D/frames/f%03d.png -vf "palettegen=max_colors=${COLORS:-128}:stats_mode=full" $D/work/pal.png
ffmpeg -v error -y -framerate $FPS -i $D/frames/f%03d.png -i $D/work/pal.png -lavfi "paletteuse=dither=${DITHER:-bayer:bayer_scale=3}:diff_mode=rectangle" -loop 0 $D/final.gif
ls -l $D/final.gif | awk '{printf "%.2f MB\n",$5/1048576}'
