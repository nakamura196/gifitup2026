#!/usr/bin/env python3
"""Download the source map (NDL IIIF tiles) into dl/ and verify it.
新訂萬國全圖 (Shirai Tsuki, 1852), NDL pid 2543045, canvas R0000004 (19370 x 13098, Public Domain Mark)
https://jpsearch.go.jp/item/dignl-2543045   https://dl.ndl.go.jp/pid/2543045
dl/R0000004-4.jpg : whole sheet at 1/4 size (the texture).  dl/japan_sf2.jpg : Japan region at 1/2 size."""
import hashlib, io, os, sys, time, urllib.request
from PIL import Image
D = os.path.dirname(os.path.abspath(__file__)) + '/dl/'
BASE = 'https://dl.ndl.go.jp/api/iiif/2543045/R0000004/'
W, H = 19370, 13098
SHA = {'R0000004-4.jpg': 'fd29d5d2adaecce0e6e4660afb2734f44a38997beaaf90a54ea3353ec09cf0c3', 'japan_sf2.jpg': 'f7fa146be7928aae90062ee9704a644e3a0d4c2bea5619102ad8fd0f5daf7f54'}
os.makedirs(D + 'tiles', exist_ok=True)

def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000: return
    for k in range(5):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'gifitup2026 fetch'}), timeout=120).read()
            if len(b) > 1000: open(path, 'wb').write(b); return
        except Exception as e:
            err = e
        time.sleep(2)
    sys.exit('download failed: %s %s' % (url, err))

def stitch(x0, y0, w, h, sf, out, q):
    """region (x0,y0,w,h) in full-resolution pixels, tiled in 1024*sf squares, assembled at 1/sf."""
    T = 1024 * sf
    img = Image.new('RGB', ((w + sf - 1) // sf, (h + sf - 1) // sf))
    for y in range(y0, y0 + h, T):
        for x in range(x0, x0 + w, T):
            tw, th = min(T, x0 + w - x), min(T, y0 + h - y)
            f = D + 'tiles/%d_%d_%d_%d.jpg' % (sf, x, y, tw)
            get(BASE + '%d,%d,%d,%d/%d,/0/default.jpg' % (x, y, tw, th, (tw + sf - 1) // sf), f)
            img.paste(Image.open(f).convert('RGB'), ((x - x0) // sf, (y - y0) // sf))
    img.save(out, quality=q)

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def ok(n): return os.path.exists(D + n) and sha(D + n) == SHA[n]
if not ok('R0000004-4.jpg'): stitch(0, 0, W, H, 4, D + 'R0000004-4.jpg', 92)
if not ok('japan_sf2.jpg'): stitch(14400, 1400, 4600, 5000, 2, D + 'japan_sf2.jpg', 95)
for n in SHA:
    if not ok(n): sys.exit('sha256 mismatch for ' + n)
print('globe: dl/ ok')
