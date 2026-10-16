#!/usr/bin/env python3
"""Download the source print (Tokyo Fuji Art Museum, CC0) into dl/ and verify it.
https://jpsearch.go.jp/item/tfam_art_db-9801  ->  https://www.fujibi.or.jp/collection/artwork/09801/
dl/tfam.webp : the museum's full-size image; dl/tfam.png : its lossless decode (what the scripts read)."""
import hashlib, os, sys, urllib.request
from PIL import Image
D = os.path.dirname(os.path.abspath(__file__)) + '/dl/'
URL = 'https://www.fujibi.or.jp/webp/assets/images/artwork/source/09801.jpg.webp'
SHA_WEBP = '3e2e59b3a75d81a817da8826538fd6be8ae07200a8131a45deb89a47ea5dc83e'
SHA_PIX = 'b0bc7b220df2e5aa93423f145ca644a08d31f09f5fbc733b5716b8ab79f97cb5'   # sha256 of the decoded RGB pixel bytes (1394 x 950)
os.makedirs(D, exist_ok=True)
w, p = D + 'tfam.webp', D + 'tfam.png'
def sha(b): return hashlib.sha256(b).hexdigest()
if not os.path.exists(w) or sha(open(w, 'rb').read()) != SHA_WEBP:
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (gifitup2026 fetch)'})
    open(w, 'wb').write(urllib.request.urlopen(req, timeout=60).read())
if sha(open(w, 'rb').read()) != SHA_WEBP:
    sys.exit('sha256 mismatch for tfam.webp (the museum file changed?)')
im = Image.open(w).convert('RGB')
if sha(im.tobytes()) != SHA_PIX:
    sys.exit('decoded pixels differ from the recorded ones (different libwebp?)')
im.save(p)
print('yose: dl/tfam.png ok', im.size)
