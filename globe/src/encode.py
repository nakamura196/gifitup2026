"""frames/*.png + durations -> one shared palette (Pillow) -> gifsicle -O3 --lossy."""
import sys, glob, os, subprocess
from PIL import Image
G = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
colors, lossy, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
dither = Image.Dither.NONE if (len(sys.argv) < 5 or sys.argv[4] == 'none') else Image.Dither.FLOYDSTEINBERG
FR = os.environ.get('FRAMES', 'frames')
files = sorted(glob.glob(f'{G}/{FR}/f*.png'))
durs = [int(x) for x in open(f'{G}/{FR}/durations.txt')]
assert len(files) == len(durs), (len(files), len(durs))
ims = [Image.open(f).convert('RGB') for f in files]
H = int(os.environ.get('CROP_H', ims[0].height))
ims = [im.crop((0, 0, im.width, H)) for im in ims]
w, h = ims[0].size
pick = ims[::max(1, len(ims)//10)][:10]
hold = ims[max(range(len(durs)), key=lambda i: durs[i])]     # the stamped frame: make sure its reds get palette slots
pick += [hold]
import numpy as np
a = np.asarray(hold).astype(int); red = (a[..., 0] - (a[..., 1] + a[..., 2])//2) > 70
if red.any():                      # give the vermilion seal its own palette slots
    ys, xs = np.where(red)
    box = (max(0, xs.min()-6), max(0, ys.min()-6), min(w, xs.max()+6), min(h, ys.max()+6))
    pick += [hold.crop(box).resize((w, h), Image.NEAREST)]
mos = Image.new('RGB', (w*4, h*3))
for k, im in enumerate(pick): mos.paste(im, ((k % 4)*w, (k//4)*h))
NRED = 10
base = mos.quantize(colors=colors - NRED, method=Image.Quantize.MEDIANCUT).getpalette()[:3*(colors - NRED)]
reds = np.zeros((1, 1, 3), np.uint8)
allpx = np.concatenate([np.asarray(im).reshape(-1, 3) for im in ims[::2]])
rm = (allpx[:, 0].astype(int) - (allpx[:, 1].astype(int) + allpx[:, 2].astype(int))//2) > 60
rp = allpx[rm][:200000]
redpal = Image.fromarray(rp.reshape(1, -1, 3)).quantize(colors=NRED, method=Image.Quantize.MEDIANCUT).getpalette()[:3*NRED] if len(rp) > 50 else base[:3*NRED]
pal = Image.new('P', (1, 1)); pal.putpalette(base + redpal + [0]*(768 - len(base) - len(redpal)))
q = [im.quantize(palette=pal, dither=dither) for im in ims]
tmp = out + '.tmp.gif'
q[0].save(tmp, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=False, disposal=1)
subprocess.run(['gifsicle', '-O3', f'--lossy={lossy}', tmp, '-o', out], check=True)
os.remove(tmp)
print(out, os.path.getsize(out), 'bytes', len(q), 'frames', sum(durs), 'ms', f'{w}x{h}')
