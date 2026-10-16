"""v3: whole sheet -> the two hemispheres lift off and wrap into one globe -> spin ->
hard stop on Japan -> move in -> the title seal stamps Japan -> pull back -> unwrap ->
the flat map now carries the stamp on Japan -> the seal hops home (= frame 1).
All pixels come from NDL 新訂萬國全圖 (dignl-2543045, canvas 4). Classical warping only."""
import sys, os, math
import numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import globe
from globe import G, EAST, WEST

W = int(os.environ.get('W', 720)); K = W / 640.0
OX, OY, S = 97.0, 30.0, 4598.0 / W
H = int(round((2985 - OY) / S))      # stop above the grey ruler
OUTDIR = os.environ.get('FRAMES', 'frames')
#         # sheet (sf4) -> output: out = (tex - O) / S
TEX_PLAIN = globe.TEX.copy()               # colour-adjusted sheet (same pixels everywhere)

def to_out(tx, ty): return (tx - OX) / S, (ty - OY) / S

# ---- seal on the title ----------------------------------------------------------
SX0, SY0, SX1, SY1 = 2135, 165, 2375, 405
patch = TEX_PLAIN[SY0:SY1, SX0:SX1]
red = patch[..., 0] - 0.5*(patch[..., 1] + patch[..., 2])
alpha = np.clip((red - 18) / 40.0, 0, 1)
paper = np.median(TEX_PLAIN[200:280, 1950:2120].reshape(-1, 3), axis=0)
SEAL = Image.fromarray(np.dstack([patch, alpha*255]).astype(np.uint8), 'RGBA')
TEX_NOSEAL = TEX_PLAIN.copy()
TEX_NOSEAL[SY0:SY1, SX0:SX1] = patch*(1 - alpha[..., None]) + paper[None, None, :]*alpha[..., None]
seal_home = to_out((SX0 + SX1)/2, (SY0 + SY1)/2)
seal_w = (SX1 - SX0) / S

# ---- Japan and the stamp ---------------------------------------------------------
JLON, JLAT = 134.0, 36.0          # Honshu as drawn (checked against 大日本)
def tex_xy(lon, lat):
    d = math.radians(lon - 70); la = math.radians(lat)
    k = 1/(1 + math.cos(la)*math.cos(d))
    return EAST[0] + math.cos(la)*math.sin(d)*k*EAST[2], EAST[1] - math.sin(la)*k*EAST[2]
JTX, JTY = tex_xy(JLON, JLAT)
c = math.acos(math.cos(math.radians(JLAT))*math.cos(math.radians(JLON-70)))
TEXPX_PER_RAD = EAST[2]*0.5/math.cos(c/2)**2
R0 = 168.0*K                      # spinning globe
R1 = float(os.environ.get('R1', 860.0)) * K   # deep zoom on Japan (Japan ~ 225 px long at 720 wide)
STAMP_SCREEN = float(os.environ.get('STAMP', 2.1)) * seal_w   # stamp size on the zoomed globe (px)
def make_stamp_tex():
    s = STAMP_SCREEN * TEXPX_PER_RAD / R1
    sp = SEAL.resize((round(s), round(s)), Image.LANCZOS).rotate(-8, Image.BICUBIC, expand=True)
    a = np.asarray(sp).astype(np.float32); a[..., 3] = np.clip(a[..., 3]*1.7, 0, 255)
    sp = Image.fromarray(a.astype(np.uint8), 'RGBA')
    base = Image.fromarray(TEX_NOSEAL.astype(np.uint8)).convert('RGBA')
    base.alpha_composite(sp, (round(JTX - sp.width/2), round(JTY - sp.height/2)))
    return np.asarray(base.convert('RGB')).astype(np.float32)
TEX_STAMP = make_stamp_tex()

# ---- high-resolution source (sf2) around Japan, for the deep zoom -------------------
import cv2
HX0, HY0 = 7200, 700                 # sf2 pixel origin of dl/japan_sf2.jpg (full-res 14400,1400)
_hi = np.asarray(Image.open(f'{G}/dl/japan_sf2.jpg').convert('RGB')).astype(np.float32)
_l = _hi.mean(axis=2, keepdims=True); _hi = _l + (_hi - _l)*globe.SAT
_hi = np.clip((_hi - globe.BLACK)*255.0/(255.0 - globe.BLACK), 0, 255)
_hi = cv2.bilateralFilter(_hi.astype(np.uint8), 11, 22, 7).astype(np.float32)
HI_PLAIN = _hi
def make_stamp_hi():
    s = 2 * STAMP_SCREEN * TEXPX_PER_RAD / R1
    sp = SEAL.resize((round(s), round(s)), Image.LANCZOS).rotate(-8, Image.BICUBIC, expand=True)
    a = np.asarray(sp).astype(np.float32); a[..., 3] = np.clip(a[..., 3]*1.7, 0, 255)
    sp = Image.fromarray(a.astype(np.uint8), 'RGBA')
    base = Image.fromarray(HI_PLAIN.astype(np.uint8)).convert('RGBA')
    base.alpha_composite(sp, (round(2*JTX - HX0 - sp.width/2), round(2*JTY - HY0 - sp.height/2)))
    return np.asarray(base.convert('RGB')).astype(np.float32)
HI_STAMP = make_stamp_hi()
HI_OF = {id(TEX_PLAIN): HI_PLAIN, id(TEX_STAMP): HI_STAMP}

# ---- sheet views ----------------------------------------------------------------
def sheet_view(tex):
    img = Image.fromarray(tex.astype(np.uint8))
    return np.asarray(img.transform((W, H), Image.EXTENT, (OX, OY, OX + W*S, OY + H*S), Image.BILINEAR)).astype(np.float32)
SHEET_SEAL = sheet_view(TEX_PLAIN)
SHEET_NOSEAL = sheet_view(TEX_NOSEAL)
SHEET_STAMP = sheet_view(TEX_STAMP)
# where the hemispheres were: blank paper (large median of the sheet itself: lines vanish, wash stays faint)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
EC = to_out(EAST[0], EAST[1]); WC = to_out(WEST[0], WEST[1]); DR = 1108 / S
hole = np.zeros((H, W), bool)
for (cx, cy) in (EC, WC):
    hole |= (xx - cx)**2 + (yy - cy)**2 < (DR + 5.0)**2
med = Image.fromarray(SHEET_NOSEAL.astype(np.uint8)).filter(ImageFilter.MedianFilter(13)).filter(ImageFilter.MedianFilter(13))
med = np.asarray(med.filter(ImageFilter.GaussianBlur(3))).astype(np.float32)
ring = np.zeros((H, W), bool)
for (cx, cy) in (EC, WC):
    r = np.sqrt((xx - cx)**2 + (yy - cy)**2); ring |= (r > DR + 7) & (r < DR + 22)
ring_paper = np.median(SHEET_NOSEAL[ring], axis=0)       # the paper right around the disks
med = med*0.22 + ring_paper[None, None, :]*0.78     # mostly flat paper: less stain, compresses better
BG_HOLES = SHEET_NOSEAL.copy(); BG_HOLES[hole] = med[hole]
BGS = np.where(hole[..., None], BG_HOLES, SHEET_SEAL)   # holes, seal still on the title

# ---- morph renderer --------------------------------------------------------------
def sample(tex, px, py):
    hi = HI_OF.get(id(tex)) if 'HI_OF' in globals() else None
    if hi is not None and px.size:
        u = px*2 - HX0; v = py*2 - HY0
        m = (u >= 1) & (v >= 1) & (u < hi.shape[1] - 2) & (v < hi.shape[0] - 2)
        if m.any():
            out = _sample(tex, px, py) if not m.all() else np.zeros(px.shape + (3,), np.float32)
            out[m] = _sample(hi, u[m], v[m])
            return out
    return _sample(tex, px, py)
def _sample(tex, px, py):
    h, w, _ = tex.shape
    px = np.clip(px, 0, w-1.001); py = np.clip(py, 0, h-1.001)
    x0 = px.astype(int); y0 = py.astype(int); fx = (px-x0)[..., None]; fy = (py-y0)[..., None]
    return (tex[y0, x0]*(1-fx) + tex[y0, x0+1]*fx)*(1-fy) + (tex[y0+1, x0]*(1-fx) + tex[y0+1, x0+1]*fx)*fy

def globe_layer(tex, cx, cy, R, lon0, lat0, flat=0.0, blur_lons=None):
    """flat=0: orthographic globe; flat=1: the flat east disk exactly as printed.
    In between, texture coordinates are blended (a classical warp)."""
    x = (xx + 0.5 - cx) / R; y = -(yy + 0.5 - cy) / R
    r2 = x*x + y*y; inside = r2 < 1.0
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    acc = np.zeros((H, W, 3), np.float32)
    lons = blur_lons or [lon0]
    xi, yi, zi = x[inside], y[inside], z[inside]
    for L in lons:
        p0 = np.radians(lat0)
        lat = np.arcsin(np.clip(zi*np.sin(p0) + yi*np.cos(p0), -1, 1))
        lon = np.radians(L) + np.arctan2(xi, zi*np.cos(p0) - yi*np.sin(p0))
        lond = (np.degrees(lon) + 180) % 360 - 180
        east = ((lond - 70 + 540) % 360 - 180)**2 <= 90**2
        out = np.zeros((len(xi), 3), np.float32)
        for disk, m in ((EAST, east), (WEST, ~east)):
            dcx, dcy, dR, dl = disk
            d = np.radians(((lond[m] - dl + 540) % 360) - 180); cl = np.cos(lat[m])
            k = 1/(1 + cl*np.cos(d))
            X = cl*np.sin(d)*k; Y = np.sin(lat[m])*k
            if flat > 0 and disk is EAST:
                X = (1-flat)*X + flat*xi[m]*(1108/1100); Y = (1-flat)*Y + flat*yi[m]*(1108/1100)
            out[m] = sample(tex, dcx + X*dR, dcy - Y*dR)
        acc[inside] += out
    acc /= len(lons)
    sh = 1 - flat
    Lv = np.array([-0.45, 0.5, 0.74]); Lv /= np.linalg.norm(Lv)
    ndl = np.clip(x*Lv[0] + y*Lv[1] + z*Lv[2], 0, 1)
    f = (0.90 + 0.13*ndl) * (0.80 + 0.20*np.sqrt(z)) + 0.03*ndl**30
    acc *= (1 - sh + sh*f)[..., None]
    a = np.clip((1 - np.sqrt(r2)) * R, 0, 1)
    return acc, a

def flat_disk_layer(tex, cx, cy, R, sx):
    """the west hemisphere as a flat disk, folding (horizontal squash sx) as it goes behind"""
    x = (xx + 0.5 - cx) / (R*max(sx, 1e-3)); y = -(yy + 0.5 - cy) / R
    r2 = x*x + y*y; inside = r2 < 1
    out = np.zeros((H, W, 3), np.float32)
    dcx, dcy, dR, _ = WEST
    out[inside] = sample(tex, dcx + x[inside]*1108, dcy - y[inside]*1108) * (0.78 + 0.22*sx)
    a = np.clip((1 - np.sqrt(r2)) * R*max(sx, 0.05), 0, 1)
    return out, a

def drop_shadow(img, cx, cy, rx, ry, dx, dy, k):
    d = ((xx - cx - dx)/rx)**2 + ((yy - cy - dy)/ry)**2
    sh = np.clip(1.15 - d, 0, 1)**1.5 * k
    return img * (1 - sh[..., None])

def compose(bg, layers, sprite=None):
    img = bg.copy()
    for col, a in layers:
        img = col*a[..., None] + img*(1 - a[..., None])
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')
    if sprite is not None:
        x, y, s, rot, lift = sprite
        w = max(4, round(seal_w*s))
        sp = SEAL.resize((w, w), Image.LANCZOS).rotate(rot, Image.BICUBIC, expand=True)
        if lift > 0:
            shd = np.asarray(sp)[..., 3].astype(np.float32)*0.22*min(1, lift)
            shimg = Image.fromarray(np.dstack([np.zeros(shd.shape + (3,)), shd]).astype(np.uint8), 'RGBA').filter(ImageFilter.GaussianBlur(4*K))
            off = round((4 + 12*lift)*K)
            im.alpha_composite(shimg, (round(x - sp.width/2 + off*0.5), round(y - sp.height/2 + off)))
        im.alpha_composite(sp, (round(x - sp.width/2), round(y - sp.height/2)))
    return im.convert('RGB')

def ease(t): return 0.5 - 0.5*math.cos(math.pi*t)
def lerp(a, b, t): return a + (b - a)*t

# globe placement
GCX, GCY = W/2, 258.0*K - OY/S                      # spinning globe centre
VLAT = JLAT - 24.0                           # Japan tilted toward us
SIN_T = math.sin(math.radians(JLAT - VLAT))
J1 = (W/2, 258.0*K - OY/S)                          # Japan on screen when moved in
def globe_frame(tex, lon, lat, R, cx, cy, bg=BG_HOLES, blur=None, sprite=None, soft=0.0):
    col, a = globe_layer(tex, cx, cy, R, lon, lat, 0.0, blur)
    if soft > 0:
        import cv2
        col = cv2.GaussianBlur(col, (0, 0), soft)
    b = drop_shadow(bg, cx, cy, R*1.0, R*0.97, 0.10*R, 0.12*R, 0.28)
    return compose(b, [(col, a)], sprite)

def wrap_frame(t, tex, bg):
    """t=0: flat sheet; t=1: one globe (east face front) at the spinning position."""
    e = ease(t)
    lift = math.sin(math.pi*min(1, t*1.3)) if t < 0.77 else max(0, 1 - (t-0.77)/0.23)*0.9
    # west disk slides toward the centre and folds away behind
    wcx = lerp(WC[0], GCX - 0.25*R0, e); wcy = lerp(WC[1], GCY, e)
    sx = max(0.0, 1 - 1.15*e)
    # east disk slides to centre and bulges into the sphere
    ecx = lerp(EC[0], GCX, e); ecy = lerp(EC[1], GCY, e); eR = lerp(DR, R0, e)
    flat = 1 - ease(min(1, t*1.15))
    b = bg
    layers = []
    if sx > 0.01:
        b = drop_shadow(b, wcx, wcy, DR*sx, DR, (4 + 10*lift)*K, (6 + 12*lift)*K, 0.22*lift)
        layers.append(flat_disk_layer(tex, wcx, wcy, DR, sx))
    b = drop_shadow(b, ecx, ecy, eR, eR, 4 + 0.12*eR*lift, 6 + 0.14*eR*lift, 0.18 + 0.12*lift)
    col, a = globe_layer(tex, ecx, ecy, eR, 70.0, 0.0, flat)
    layers.append((col, a))
    return compose(b, layers)

FD = 60
frames = []
def add(im, d=FD): frames.append((im, d))

# 1 the whole sheet (loop point)
add(Image.fromarray(SHEET_SEAL.astype(np.uint8)), 700)
# 2 wrap
WRAP_T = [0.25, 0.55, 0.85, 1.0]
for t in WRAP_T:
    add(wrap_frame(t, TEX_PLAIN, BGS))
if os.environ.get('SPIN', 'slow') == 'fast':
    # 3 spin (from rest at lon 70, lat 0), brake, land past Japan, spring back
    OVER = 20.0
    total = (JLON - 360.0 - OVER) - 70.0           # negative: surface moves left->right
    ACC, FULL, BRAKE = 1, 0, 2
    V = total / (ACC/2 + FULL + BRAKE/2)
    segs = []
    lon = 70.0
    for i in range(ACC):
        t1 = (i+1)/ACC; L1 = 70.0 + V*ACC/2*t1*t1; segs.append((lon, L1)); lon = L1
    for i in range(FULL):
        segs.append((lon, lon + V)); lon += V
    b0 = lon
    for i in range(BRAKE):
        p = lambda t: t - t*t/2
        L1 = b0 + V*BRAKE*p((i+1)/BRAKE); segs.append((lon, L1)); lon = L1
    n = len(segs)
    SPAN = 2.6
    for k, (L0, L1) in enumerate(segs):
        m = (L0 + L1)/2; half = (L1 - L0)*SPAN/2
        nb = max(2, int(abs(2*half)/4))
        lat = lerp(0.0, VLAT, ease((k+1)/n))
        add(globe_frame(TEX_PLAIN, m, lat, R0, GCX, GCY, bg=BGS, blur=[m - half + 2*half*j/(nb-1) for j in range(nb)]))
    WOB = [(-OVER, -OVER*0.0), ]
    prev = JLON - OVER
    for k, off in enumerate([OVER*0.35, 0.0]):
        L = JLON + off
        nb = max(1, int(abs(L - prev)/3))
        blur = [prev + (L - prev)*j/max(1, nb-1) for j in range(nb)] if (nb > 1 and k < 1) else None
        add(globe_frame(TEX_PLAIN, L, VLAT, R0, GCX + (3*K if k == 0 else 0), GCY, bg=BGS, blur=blur), FD if k < 1 else 320)
        prev = L

else:
    # 3 a readable spin: sharp frames, ease in, ease out with a small overshoot onto Japan
    SPIN_N = int(os.environ.get('SPIN_N', 18))
    SPIN_FD = int(os.environ.get('SPIN_FD', 60))
    SOFT = float(os.environ.get('SOFT', 0.0))
    total = (JLON - 360.0) - 70.0                  # -296 deg: surface moves left->right
    OVS = 0.055
    NB = 3                                          # frames for the overshoot settle
    nf = SPIN_N - NB
    vel = []
    for k in range(nf):
        u = (k + 0.5) / nf
        vel.append(min(1.0, u/0.18) * (1 if u < 0.42 else (1 - (u - 0.42)/0.58)**1.6 + 0.04))
    tot = sum(vel); pos = [0.0]
    for v in vel: pos.append(pos[-1] + v/tot*(1 + OVS))
    for k in range(1, NB + 1):
        u = k / NB; pos.append(1 + OVS*(1 - u*u*(3 - 2*u)))
    def prof(t): return pos[round(t*SPIN_N)]
    prev = 70.0
    for k in range(1, SPIN_N + 1):
        t = k / SPIN_N
        L = 70.0 + total*prof(t)
        lat = lerp(0.0, VLAT, ease(min(1, t*1.2)))
        step = abs(L - prev)
        blur = None
        add(globe_frame(TEX_PLAIN, L, lat, R0, GCX, GCY, bg=BGS, blur=blur, soft=(SOFT if k < SPIN_N - 3 else 0.0)), SPIN_FD if k < SPIN_N else 320)
        prev = L

# 4 the seal lifts off the title and leaps up out of the frame
BG_HOLES_NS = BG_HOLES
hx, hy = seal_home
jy0 = GCY - R0*SIN_T
for t, s_, rot, lift in [(0.0, 1.12, 0, 0.4), (0.5, 1.4, 10, 1.0)]:
    y = hy - 8*K*lift - t*(hy + 60*K)
    add(globe_frame(TEX_PLAIN, JLON, VLAT, R0, GCX, GCY, bg=BG_HOLES_NS, sprite=(hx + 30*K*t, y, s_, rot, lift)))
# 5 deep zoom on Japan (sharp: high-resolution tiles), Japan ends in the middle of the frame
J1 = (W/2, H/2)
def jcy(jy, R, lat): return jy + R*math.sin(math.radians(JLAT - lat))
ZOOM = [0.5, 1.0]
for k, e in enumerate(ZOOM):
    ee = ease(e) if k < len(ZOOM) - 1 else 1.0
    R = R0*(R1/R0)**ee; lat = lerp(VLAT, JLAT, ee); jy = lerp(jy0, J1[1], ee)
    add(globe_frame(TEX_PLAIN, JLON, lat, R, GCX, jcy(jy, R, lat), bg=BG_HOLES_NS), FD if k < len(ZOOM) - 1 else 500)
CY1 = jcy(J1[1], R1, JLAT)
# 6 the seal drops in from above and stamps Japan
tx, ty = J1
big = STAMP_SCREEN / seal_w
for t, s_, rot, lift in [(0.0, big*1.35, 6, 1.0), (0.55, big*1.25, 0, 0.7), (0.9, big*1.08, -6, 0.25)]:
    y = lerp(-0.6*big*seal_w, ty, t*t*(1/0.81) if t < 0.9 else 1.0) if t < 0.9 else ty - 4*K
    add(globe_frame(TEX_PLAIN, JLON, JLAT, R1, GCX, CY1, bg=BG_HOLES_NS, sprite=(tx + 20*K*(1 - t), y, s_, rot, lift)))
add(globe_frame(TEX_STAMP, JLON, JLAT, R1, GCX, CY1, bg=BG_HOLES_NS), 1000)
# 6b pull back: shrink and turn back to the east face (lon 70, lat 0), ready to unwrap
for e in (0.5, 1.0):
    ee = ease(e)
    R = R1*(R0/R1)**ee; lon = lerp(JLON, 70.0, ee); lat = lerp(JLAT, 0.0, ee)
    add(globe_frame(TEX_STAMP, lon, lat, R, GCX, lerp(CY1 - R1, GCY - R0, ee) + R))
# 7 unwrap (reverse of wrap, now with the stamp; title seal is away)
BGU = np.where(hole[..., None], BG_HOLES, SHEET_NOSEAL)
for t in reversed(WRAP_T[:-1]):
    add(wrap_frame(t, TEX_STAMP, BGU))
add(Image.fromarray(SHEET_STAMP.astype(np.uint8)), 500)
# 8 the seal hops from flat Japan back to the title
fjx, fjy = to_out(JTX, JTY)
BACK = [(0.0, 0.55, -8, 0.4), (0.35, 1.25, -2, 1.0), (0.72, 1.3, 3, 1.0), (0.94, 1.08, 1, 0.35)]
for t, s, rot, lift in BACK:
    x = lerp(fjx, hx, t); y = lerp(fjy, hy, t) - 45*K*math.sin(math.pi*t)
    add(compose(SHEET_NOSEAL, [], sprite=(x, y, s, rot, lift)))

FD_ = f'{G}/{OUTDIR}'
os.makedirs(FD_, exist_ok=True)
for fn in os.listdir(FD_):
    if fn.startswith('f') and fn.endswith('.png'): os.remove(f'{FD_}/{fn}')
with open(f'{FD_}/durations.txt', 'w') as fh:
    for k, (im, d) in enumerate(frames):
        im.save(f'{FD_}/f{k:03d}.png'); fh.write(f'{d}\n')
print(len(frames), 'frames', sum(d for _, d in frames), 'ms', W, 'x', H)
