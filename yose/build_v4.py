#!/usr/bin/env python3
"""GIF IT UP 2026 - yose v4 (Kuniyoshi, "Mikake wa kowai ga tonda ii hito da").

Reproducible build:  python3 build_v4.py   (runs complete.py first)
Inputs : dl/tfam.png (fetched by fetch.py; Tokyo Fuji Art Museum, CC0) + work/masks_traced/{jaw,hand_upper,hand_lower}.png
         completed figures from complete.py -> work/completed/layers_v4.npz
Output : ../build/yose.gif (+ strips in ../build/yose_work/)
All pixels come from the source print; no generative AI. Classical image ops only (numpy/OpenCV/Pillow).
"""
import math, os
import numpy as np, cv2
from PIL import Image
import subprocess, sys

D = os.path.dirname(os.path.abspath(__file__)) + '/'
B = os.path.abspath(D + '../build/yose_work') + '/'; os.makedirs(B, exist_ok=True)
subprocess.run([sys.executable, D + 'complete.py'], check=True, stdout=subprocess.DEVNULL)
CL = np.load(B + 'completed/layers_v4.npz')
SCALE, NC, FD = 0.6, 96, 50          # output scale, palette size, frame duration (ms)

src = np.asarray(Image.open(D + 'dl/tfam.png').convert('RGB')).astype(np.float32)
H, W = src.shape[:2]
R_, G_, B_ = src[..., 0], src[..., 1], src[..., 2]
blue = (B_ > R_ + 8)

def load_alpha(n):
    return np.asarray(Image.open(D + 'work/masks_traced/%s.png' % n)).astype(np.float32) / 255.
A_JAW, A_UP, A_LO = load_alpha('jaw'), load_alpha('hand_upper'), load_alpha('hand_lower')
# adjustment: the thick inner stroke of the mouth corner (his own outline facing the open mouth)
# was left on the face by the trace; it moves with the jaw man so it does not float in the hole
_box = np.zeros((H, W), bool); _box[770:832, 370:412] = True
_arc = _box & (src.mean(-1) < 110) & (A_UP == 0) & (A_LO == 0)
A_JAW = np.maximum(A_JAW, _arc.astype(np.float32))
M_JAW, M_UP, M_LO = A_JAW > 0, A_UP > 0, A_LO > 0

def polym(pts):
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.array(pts, np.int32)], 1); return m.astype(bool)

# ---------------- plate: the print with the three men removed ----------------
# blank blue paper below the hand, made periodic with cross-faded seams
# (two crease-free pieces either side of a paper crease, joined with a cross-fade)
_a, _b = src[1260:1394, 140:258], src[1260:1394, 290:396]; _o = 20; _r = np.linspace(0, 1, _o)[None, :, None]
P = np.concatenate([_a[:, :-_o], _a[:, -_o:] * (1 - _r) + _b[:, :_o] * _r, _b[:, _o:]], 1)
pm = P.reshape(-1, 3).mean(0); o = 24; h, w = P.shape[:2]
ra = np.linspace(0, 1, o)[:, None, None]
T = P.copy(); T[:o] = P[:o] * ra + P[h - o:] * (1 - ra); T = T[:h - o]
ca = np.linspace(0, 1, o)[None, :, None]
T2 = T.copy(); T2[:, :o] = T[:, :o] * ca + T[:, w - o:] * (1 - ca); T = T2[:, :w - o]
th, tw = T.shape[:2]
ys, xs = np.mgrid[0:H, 0:W]
tex = T[ys % th, xs % tw]
anym = M_JAW | M_UP | M_LO
hole = cv2.dilate(anym.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
bw = (blue & ~hole).astype(np.float32)
num = cv2.GaussianBlur(src * bw[..., None], (0, 0), 35); den = cv2.GaussianBlur(bw, (0, 0), 35)[..., None] + 1e-4
fillc = tex - pm + num / den
# for the hand men, keep the original picture in a seam band next to each other / the kimono,
# so a small relative movement shows their own pixels, never a hole
# the non-moving picture next to the men: skin/kimono colours or solid ink, not the pale paper fringe
_sp = (~anym & ((R_ > B_ + 12) | (src.mean(-1) < 90))).astype(np.uint8)
_n, _cc, _st, _ = cv2.connectedComponentsWithStats(_sp, connectivity=8)
_big = np.zeros(_n, bool); _big[1:] = _st[1:, cv2.CC_STAT_AREA] >= 400
static_pic = _big[_cc]
band_static = cv2.dilate(static_pic.astype(np.uint8), np.ones((17, 17), np.uint8)).astype(bool)
band_pair = (cv2.dilate(M_UP.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool) & M_LO) | \
            (cv2.dilate(M_LO.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool) & M_UP)
keep = np.zeros((H, W), bool)          # v4: no static seam strip; the completed bodies move whole
# the jaw man meets the face along a shared ink line: keep a 2 px band of the original there,
# so his antialiased edge never shows blue at rest, and the face keeps its own outline while he is away
jaw_edge = (M_JAW & ~_arc) & cv2.dilate(static_pic.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
keep |= jaw_edge
fillmask = hole & ~keep & ~static_pic
plate = src.copy(); plate[fillmask] = fillc[fillmask]

# ---------------- pupils (eyes are not part of any man) ----------------
EYES = [dict(c=(236, 563), r=21, poly=[(200,560),(204,546),(215,536),(232,531),(252,535),(268,544),(281,556),(279,569),(266,580),(250,588),(230,588),(212,580)]),
        dict(c=(385, 583), r=22, poly=[(357,575),(362,560),(374,549),(395,545),(418,548),(433,556),(428,571),(416,591),(400,604),(378,606),(363,596)])]
p8 = np.clip(plate, 0, 255).astype(np.uint8)
for e in EYES:
    disc = np.zeros((H, W), np.uint8); cv2.circle(disc, e['c'], e['r'], 1, -1)
    ep = polym(e['poly']).astype(np.uint8)
    p8 = cv2.inpaint(p8, (cv2.dilate(disc, np.ones((5, 5), np.uint8)) & ep) * 255, 7, cv2.INPAINT_TELEA)
    e['disc'] = (cv2.dilate(disc, np.ones((5, 5), np.uint8)) & ep).astype(np.float32); e['ep'] = ep.astype(bool)
plate = p8.astype(np.float32)
for e in EYES: e['clip'] = (e['ep'] | (e['disc'] > 0)).astype(np.float32)   # identical to the print at rest

# ---------------- layers ----------------
FOOT = polym([(253,794),(302,794),(304,814),(296,823),(260,823),(252,812)]).astype(np.float32)
ANKLE = np.array([284., 823.])
JRGB = CL['jaw_rgb'].astype(np.float32); JA = CL['jaw_a']
LRGB = CL['lo_rgb'].astype(np.float32); LA = CL['lo_a']
# the completed parts fade in as soon as a man leaves his place (weight w), so the rest pose equals the print
JA_ADD = np.clip(JA - A_JAW, 0, 1); LA_ADD = np.clip(LA - A_LO, 0, 1)
def jaw_layers(w):
    a = np.clip(A_JAW + w * JA_ADD, 0, 1)
    return np.dstack([JRGB, a * (1 - FOOT)]), np.dstack([JRGB, a * FOOT])
def lo_layer(w):
    return np.dstack([LRGB, np.clip(A_LO + w * LA_ADD, 0, 1)])
L_UP = np.dstack([src, CL['up_a']])
FACE = CL['face'].astype(np.float32); FACE_ADD = cv2.GaussianBlur(CL['face_added'].astype(np.float32), (0, 0), 0.5)[..., None]
CJ = np.array([349., 817.]); TOPY = 626.          # jaw man centroid, top of his figure
PW = np.array([515., 1230.])   # common wrist pivot of the two hand men
PU = np.array([300., 1070.]); PL = np.array([300., 1150.])   # pivots for their own small moves

def Rm(a):
    a = math.radians(a); return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
def M(c0, a=0., d=(0., 0.), sx=1., sy=1.):
    """scale (sx,sy) and rotate a deg (clockwise on screen) about c0, then translate by d"""
    L2 = Rm(a) @ np.diag([sx, sy]); m = np.zeros((2, 3)); m[:, :2] = L2; m[:, 2] = c0 + np.array(d) - L2 @ c0; return m
def chain(m1, m2):
    return (np.vstack([m1, [0, 0, 1]]) @ np.vstack([m2, [0, 0, 1]]))[:2]
def comp(canvas, layer, m):
    out = cv2.warpAffine(layer, m.astype(np.float32), (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    al = out[..., 3:4]; canvas *= (1 - al); canvas += out[..., :3] * al
def pupils(canvas, dx, dy):
    for e in EYES:
        mm = np.float32([[1, 0, dx], [0, 1, dy]])
        s = cv2.warpAffine(src, mm, (W, H), flags=cv2.INTER_LINEAR)
        m = (cv2.warpAffine(e['disc'], mm, (W, H), flags=cv2.INTER_LINEAR) * e['clip'])[..., None]
        canvas *= (1 - m); canvas += s * m
def ease(t): t = min(1., max(0., t)); return t * t * (3 - 2 * t)
def key(f, ks):
    fs = sorted(ks)
    if f <= fs[0]: return ks[fs[0]]
    for i in range(len(fs) - 1):
        if fs[i] <= f <= fs[i + 1]:
            t = (f - fs[i]) / (fs[i + 1] - fs[i]); return ks[fs[i]] + (ks[fs[i + 1]] - ks[fs[i]]) * ease(t)
    return ks[fs[-1]]

# ---------------- timeline (80 frames x 50 ms = 4.0 s) ----------------
N = 80
# both men together (about the wrist): catch, then springboard
HAND_K = {0: 0, 28: 0, 29: -3.0, 30: -1.0, 31: 0.8, 33: 0, 50: 0, 53: -3.5, 54: -4.0, 55: 4.0, 57: 2.5, 60: 0}
# each man on his own, kept small so the shared outline never opens wider than the seam band
UP_K = {0: 0, 29: 0, 30: 1.2, 32: 0, 80: 0}
# split beat: the upper man sits up off the lower man (about the wrist), carrying the jaw man, then lies back
SPLIT_A = {0: 0, 35: 0, 38: 9.0, 45: 9.0, 48: 0, 80: 0}
SPLIT_D = {0: 0, 35: 0, 38: -4.0, 45: -4.0, 48: 0, 80: 0}
PS = np.array([528., 1195.])   # he sits up about his own bottom, which stays tucked under the kimono
LO_K = {0: 0, 29: 0, 30: -1.0, 32: 0, 36: 0, 39: -2.0, 45: -2.0, 48: 0, 80: 0}   # lower man: sinks a little as the other sits up
LAND = np.array([-15., 128.])          # jaw man's offset when sitting in the palm (upper man at rest)

def jaw_pose(f, up_m):
    """returns (matrix, foot angle, pupil dx, dy)"""
    ty = TOPY - CJ[1]
    if f < 10 or f >= 71:
        sy = key(f, {71: 0.94, 72: 1.03, 73: 1.0}) if f >= 71 else 1.0
        d = (0, (1 - sy) * (929 - CJ[1]))                  # snap about his bottom
        pd = (0, 0) if f < 10 else (key(f, {71: 0, 79: 0}), key(f, {71: -3, 76: 0}))
        return M(CJ, 0, d, 1 / math.sqrt(sy), sy), 0., pd
    if f <= 20:                                                   # yawn: stretch from the top
        sy = 1 + 0.03 * ease((f - 10) / 7)
        return M(CJ, 0, (0, -(sy - 1) * ty), 1.0, sy), 0., (0.5 * (sy - 1) / 0.03, -5 * (sy - 1) / 0.03)
    if f <= 28:                                                   # slips and drops into the hand
        t = (f - 20) / 8; g = t * t
        sy = 1.03 + (1 - 1.03) * t
        d = np.array([0, -(sy - 1) * ty]) * (1 - t) + LAND * g
        a = 7 * math.sin(math.pi * t)
        return M(CJ, a, d, 1, sy), 0., ((-4, 7) if f >= 22 else (0.5, -5))
    if f <= 54:                                                   # in the palm: rides on the upper man
        sq = key(f, {29: 0.86, 30: 0.95, 31: 1.04, 33: 1.0, 51: 1.0, 54: 0.88})
        wig = key(f, {37: 0, 38: 6, 40: -6, 42: 6, 44: -6, 46: 5, 48: -4, 50: 0}) if 37 <= f <= 50 else 0.
        foot = key(f, {36: 0, 38: -45, 40: 10, 42: -45, 44: 10, 46: -45, 48: 10, 50: 0}) if 36 <= f <= 50 else 0.
        bottom = CJ + LAND + np.array([0, 929 - CJ[1]])
        local = chain(M(bottom, wig, (0, 0), 1 / math.sqrt(sq), sq), M(CJ, 0, LAND))
        pdx = key(f, {29: -4, 36: -6, 42: -3, 48: -6, 54: -4})
        return chain(up_m, local), foot, (pdx, 7)
    # 55..70: jumps out of the hand, somersault, lands back in the face
    t = (f - 54) / 16
    st = M(CJ, 0, LAND)
    start = np.array(st[:, 2]) + CJ - st[:, :2] @ CJ
    d = LAND * (1 - t); d = d.copy(); d[1] -= 4 * 230 * t * (1 - t)
    a = -360 * ease(t)
    sy = 1.1 if f <= 56 else 1.0
    pd = (-4 + 4 * t, 7 - 13 * min(1, t / 0.55) if t < 0.55 else -6 + 6 * (t - 0.55) / 0.45)
    return M(CJ, a, d, 1 / math.sqrt(sy), sy), 0., pd

frames = []
for f in range(N):
    ha, sa, la = key(f, HAND_K), key(f, SPLIT_A), key(f, LO_K)
    hw = M(PW, ha)
    up = chain(hw, chain(M(PS, sa, (0, key(f, SPLIT_D))), M(PU, key(f, UP_K)))); lo = chain(hw, M(PL, la))
    mj, foot, (pdx, pdy) = jaw_pose(f, up)
    # how far each man is from his place (px at his far end), used to fade in the completed parts
    jd = np.abs(mj[:, :2] - np.eye(2)).max() * 300 + np.abs(mj[:, 2] + mj[:, :2] @ CJ - CJ).max()
    w_j = float(min(1., jd / 3.))
    w_l = float(min(1., (abs(ha) + abs(sa) + abs(la)) / 1.0))
    if jd < 1e-6 and w_l == 0 and pdx == 0 and pdy == 0 and foot == 0:
        full = src.astype(np.uint8)                      # rest pose: exactly the print
    else:
        c = plate.copy()
        fa = FACE_ADD * w_j; c = c * (1 - fa) + FACE * fa  # neighbours completed while he is away
        pupils(c, pdx, pdy)
        comp(c, lo_layer(w_l), lo); comp(c, L_UP, up)
        lj, lf = jaw_layers(w_j)
        comp(c, lj, mj); comp(c, lf, chain(mj, M(ANKLE, foot)))
        full = np.clip(c, 0, 255).astype(np.uint8)
    frames.append((full, Image.fromarray(full).resize((round(W * SCALE), round(H * SCALE)), Image.LANCZOS)))

small = [s for _, s in frames]
big = Image.new('RGB', (small[0].width * 3, small[0].height))
for i, k in enumerate([0, 42, 62]): big.paste(small[k], (i * small[0].width, 0))
pal = big.quantize(NC, method=Image.Quantize.MEDIANCUT)
q = [s.quantize(palette=pal, dither=Image.Dither.NONE) for s in small]
q[0].save(D + '../build/yose.gif', save_all=True, append_images=q[1:], duration=[FD] * N, loop=0, disposal=1)

KS = [0, 26, 32, 38, 42, 50, 56, 62]
tw_ = 240; th_ = round(small[0].height * tw_ / small[0].width)
strip = Image.new('RGB', (tw_ * 8, th_), 'white')
for i, k in enumerate(KS): strip.paste(small[k].resize((tw_, th_), Image.LANCZOS), (i * tw_, 0))
strip.save(B + 'strip.jpg', quality=88)
# full-resolution close-ups of the jaw/hand area (x 90-600, y 600-1300), 8 frames in 2 rows
cw, ch = 510, 700
cs = Image.new('RGB', (cw * 4, ch * 2), 'white')
for i, k in enumerate(KS):
    cs.paste(Image.fromarray(frames[k][0][600:1300, 90:600]), ((i % 4) * cw, (i // 4) * ch))
cs.save(B + 'strip_closeup.jpg', quality=88)
if os.environ.get('DUMP'):
    os.makedirs(B + 'frames4', exist_ok=True)
    for k, (fu, _) in enumerate(frames): Image.fromarray(fu).save(B + 'frames4/%02d.png' % k)
print('final.gif %.3f MB, %d frames x %d ms = %.1f s, %dx%d' % (os.path.getsize(D + '../build/yose.gif') / 1e6, N, FD, N * FD / 1000, small[0].width, small[0].height))
