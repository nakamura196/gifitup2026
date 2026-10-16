#!/usr/bin/env zsh
# Usage: zsh build.zsh [yose|mushi|globe ...]   (no argument = all three)
# fetch sources (verified by sha256) -> build -> compare md5 with checksums.md5
set -euo pipefail
R=${0:A:h}; cd $R
mkdir -p build
targets=($@); (( $# )) || targets=(yose mushi globe)
for n in $targets; do
  print "== $n"
  python3 $R/$n/fetch.py
  case $n in
    yose)  python3 $R/yose/build_v4.py ;;
    mushi) zsh $R/mushi/src/make.zsh >/dev/null ;;
    globe) FRAMES=../build/globe_frames W=640 SPIN=slow SOFT=1.3 SPIN_N=15 SPIN_FD=75 python3 $R/globe/src/build4.py
           FRAMES=../build/globe_frames python3 $R/globe/src/encode.py 96 400 $R/build/globe.gif ;;
    *) print "unknown: $n"; exit 1 ;;
  esac
done
print "\n== md5"
rc=0
for n in $targets; do
  want=$(grep " build/$n.gif" checksums.md5 | cut -d' ' -f1)
  got=$(md5 -q build/$n.gif)
  if [[ $got == $want ]]; then print "OK    $n $got"; else print "DIFF  $n got $got want $want"; rc=1; fi
done
exit $rc
