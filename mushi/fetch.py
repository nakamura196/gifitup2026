#!/usr/bin/env python3
"""Download the source page (NDL IIIF) into dl/ and verify it.
Kurimoto Tanshu, Senchufu (千蟲譜), NDL pid 2576062, canvas R0000083 (Public Domain Mark)
https://jpsearch.go.jp/item/dignl-2576062   https://dl.ndl.go.jp/pid/2576062"""
import hashlib, os, sys, urllib.request
D = os.path.dirname(os.path.abspath(__file__)) + '/dl/'
URL = 'https://dl.ndl.go.jp/api/iiif/2576062/R0000083/full/2800,/0/default.jpg'
SHA = '631623bfeec39c0aa0c9656e85ee02c195a2c506de6741ba9e39f69535685f62'
os.makedirs(D, exist_ok=True)
f = D + 'p83.jpg'
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
if not os.path.exists(f) or sha(f) != SHA:
    open(f, 'wb').write(urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'gifitup2026 fetch'}), timeout=120).read())
if sha(f) != SHA: sys.exit('sha256 mismatch for p83.jpg')
print('mushi: dl/p83.jpg ok')
