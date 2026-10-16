#!/usr/bin/env zsh
# One command: source image -> ../build/mushi.gif
# Source: Kurimoto Tanshu, Senchufu 3 vols [2], NDL pid 2576062, canvas 83 (Public Domain Mark)
#   https://jpsearch.go.jp/item/dignl-2576062
# Usage: zsh mushi/src/make.zsh   (needs python3 with numpy, opencv, pillow; ffmpeg; run fetch.py first)
set -euo pipefail
S=${0:A:h}; M=${S:h}; D=${M:h}/build/mushi_work
export DL=$M/dl
mkdir -p $D/work $D/frames
python3 $S/masks.py $D >/dev/null
CROP=280,330,2600,1900 OUTW=1080 python3 $S/build3.py $D
COLORS=128 zsh $S/encode.sh $D
python3 $S/strip.py $D 0,15,20,25,46,56,66,76
python3 $S/emstrip.py $D 40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70 $D/strip_emergence.jpg
cp $D/final.gif ${M:h}/build/mushi.gif
md5 -q ${M:h}/build/mushi.gif
