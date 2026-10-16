#!/usr/bin/env python3
"""Complete the hidden parts of the moving men and of the jaw man's neighbours (still images for review).

Classical methods only: masks, morphological closing / ellipse for the hidden outline, smoothing of the
outline, mirror-texture copy of the same figure's own pixels, flat ink in the print's own ink colour.
python3 complete.py  ->  work/completed/*.png, completion_overlay.png, sheet.jpg
"""
import os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__)) + '/'
B = os.path.abspath(D + '../build/yose_work') + '/'; os.makedirs(B, exist_ok=True)   # intermediates (not committed)
OUT = B + 'completed/'; os.makedirs(OUT, exist_ok=True)
src = np.asarray(Image.open(D + 'dl/tfam.png').convert('RGB')).astype(np.float32)
H, W = src.shape[:2]
R_, G_, B_ = src[..., 0], src[..., 1], src[..., 2]
mean = src.mean(-1)
blue = (B_ > R_ + 8)
INK = np.array([62., 50., 41.])                    # median of the print's outline ink near the face
def ld(n): return np.asarray(Image.open(D + 'work/masks_traced/%s.png' % n)).astype(np.float32) / 255.
A = {'jaw': ld('jaw'), 'hand_upper': ld('hand_upper'), 'hand_lower': ld('hand_lower')}
# the thick mouth-corner stroke belongs to the jaw man (as in v3)
_box = np.zeros((H, W), bool); _box[770:832, 370:412] = True
A['jaw'] = np.maximum(A['jaw'], (_box & (mean < 110) & (A['hand_upper'] == 0) & (A['hand_lower'] == 0)).astype(np.float32))
# drop the pale-blue paper fringe still inside the outer edge of each mask (within 3 px of the edge)
for _k in A:
    _m = (A[_k] > 0).astype(np.uint8)
    _edge = cv2.distanceTransform(_m, cv2.DIST_L2, 5) <= 3
    A[_k][_edge & (B_ > R_ + 3) & (mean > 120)] = 0
Mk = {k: v > 0.5 for k, v in A.items()}
anym = Mk['jaw'] | Mk['hand_upper'] | Mk['hand_lower']
_sp = (~anym & ((R_ > B_ + 12) | (mean < 90))).astype(np.uint8)
_n, _cc, _st, _ = cv2.connectedComponentsWithStats(_sp, connectivity=8)
_big = np.zeros(_n, bool); _big[1:] = _st[1:, cv2.CC_STAT_AREA] >= 400
static_pic = _big[_cc]

def ell(c, ax, ang=0):
    m = np.zeros((H, W), np.uint8); cv2.ellipse(m, (int(c[0]), int(c[1])), (int(ax[0]), int(ax[1])), ang, 0, 360, 1, -1); return m.astype(bool)
def polym(pts):
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.array(pts, np.int32)], 1); return m.astype(bool)
def close(m, k):
    return cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))).astype(bool)
def smooth_mask(m, s=2.0):
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), s) > 0.5

def mirror_fill(rgb, own, add):
    """fill `add` with the figure's own pixels reflected across its outline (texture copy, no synthesis)"""
    d, lab = cv2.distanceTransformWithLabels((~own).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.where(own)
    idx = np.zeros(lab.max() + 1, np.int64); idx[lab[own]] = np.arange(len(xs))
    ty, tx = np.where(add)
    k = idx[lab[ty, tx]]
    ny, nx = ys[k], xs[k]
    # reflect, stepping a bit further inside so the copied pixels are skin/cloth, not the outline ink
    ry = np.clip(2 * ny - ty + np.sign(ny - ty) * 4, 0, H - 1); rx = np.clip(2 * nx - tx + np.sign(nx - tx) * 4, 0, W - 1)
    out = rgb.copy()
    ok = own[ry, rx] & (mean[ry, rx] > 140)
    out[ty[ok], tx[ok]] = rgb[ry[ok], rx[ok]]
    # pixels whose reflection hit ink/outside: take the median skin of the figure near them
    bad = ~ok
    if bad.any():
        skin = own & (mean > 150) & (R_ > B_ + 40)
        # tile of the same figure's plain skin around the nearest skin pixel (no flat colour)
        skin = own & (mean > 150) & (R_ > B_ + 40)
        _d, _l = cv2.distanceTransformWithLabels((~skin).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        sy2, sx2 = np.where(skin); ix = np.zeros(_l.max() + 1, np.int64); ix[_l[skin]] = np.arange(len(sx2))
        by, bx = ty[bad], tx[bad]; kk = ix[_l[by, bx]]
        cy2 = np.clip(sy2[kk] - 6 + (by % 12), 0, H - 1); cx2 = np.clip(sx2[kk] - 6 + (bx % 12), 0, W - 1)
        okk = skin[cy2, cx2]
        cy2 = np.where(okk, cy2, sy2[kk]); cx2 = np.where(okk, cx2, sx2[kk])
        out[by, bx] = rgb[cy2, cx2]
    return out

def ink_edge(rgb, alpha, mask, zone, width=2.6):
    """paint the print's ink along the outline of `mask` where it runs through `zone` (the hidden part)"""
    m8 = mask.astype(np.uint8)
    dist_in = cv2.distanceTransform(m8, cv2.DIST_L2, 5)
    band = mask & (dist_in <= width) & cv2.dilate(zone.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    # already inked there? (original outline within 2 px) -> leave the print's own line
    has_ink = cv2.dilate((mean < 110).astype(np.uint8) * (alpha > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~zone
    band &= ~has_ink
    a = cv2.GaussianBlur(band.astype(np.float32), (0, 0), 0.6)
    out = rgb * (1 - a[..., None]) + INK * a[..., None]
    return out, band

def complete_person(name, zone_extra=None, k=31, extra=None, limit=None, hull=None, recut=None):
    own = Mk[name].copy()
    if recut is not None:
        # the old cut outline inside a region that is being rounded out is re-filled with skin
        own_orig = own.copy()
        edge = own & ~cv2.erode(own.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
        own &= ~(recut & edge & (mean < 150))
    others = (anym & ~own) | static_pic                       # where this man could have been hidden
    add = close(own, k) & ~own & others
    if limit is not None: add &= limit
    if extra is not None: add |= extra & ~own
    if hull is not None:
        cs, _ = cv2.findContours(((own | add) & hull).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        hm = np.zeros((H, W), np.uint8)
        for c in cs: cv2.fillPoly(hm, [cv2.convexHull(c)], 1)
        add |= hm.astype(bool) & hull & ~own
    new = smooth_mask(own | add) | own
    add = new & ~own
    rgb = mirror_fill(src, own, add)
    zone = add | cv2.dilate(others.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)   # every outline that was hidden by someone
    # anything in the added area (or the re-cut outline) that is neither skin nor ink -> nearest own skin
    fixz = add | (recut & new if recut is not None else np.zeros((H, W), bool))
    rr, bb_, mm_ = rgb[..., 0], rgb[..., 2], rgb.mean(-1)
    odd = fixz & ~(rr > bb_ + 40) & ~(mm_ < 105)
    if odd.any():
        # tile of his own plain skin (inside his buttock, x 330-400 y 840-870, no lines)
        oy, ox = np.where(odd)
        rgb[oy, ox] = src[840 + (oy % 30), 330 + (ox % 70)]
        add = add | odd
    rgb, inked = ink_edge(rgb, A[name] + add, new, zone)
    alpha = np.maximum(A[name], new.astype(np.float32))
    alpha = np.where(add, cv2.GaussianBlur(new.astype(np.float32), (0, 0), 0.7), alpha)
    return rgb, alpha, add | inked

res = {}
# jaw man: back (right side, under the cheek figure), head (top hidden under the nose), arm top edge,
# loincloth tucked at the hip. Head drawn as an ellipse continuing the visible face.
head = ell((381, 707), (34, 30), -10)
yy_ = np.mgrid[0:H, 0:W][0]
# back: round out his right side where the cheek figure covered it (only x > 440)
back_limit = np.zeros((H, W), bool); back_limit[700:900, 440:520] = True
# arm: thicker upper arm tapering to the elbow, rounded shoulder rising into the neck under the head
arm = np.zeros((H, W), np.uint8)
cv2.fillPoly(arm, [np.array([(236, 743), (262, 739), (290, 735), (314, 729), (334, 721), (348, 714), (356, 713), (360, 740), (300, 752), (240, 750)], np.int32)], 1)
# hips: close the cut corner with a round buttock continuing the back line into the lower outline
hip = np.zeros((H, W), np.uint8)
cv2.ellipse(hip, (432, 862), (40, 50), -20, 0, 360, 1, -1)
hip = hip.astype(bool) & (yy_ > 820)
hipwin = np.zeros((H, W), bool); hipwin[815:935, 405:500] = True
res['jaw'] = complete_person('jaw', k=41, extra=head | arm.astype(bool) | hip, limit=back_limit, hull=hipwin, recut=hip)
# the upper man lies on top: nothing of him was hidden, his outline is already complete
res['hand_upper'] = (src.copy(), A['hand_upper'], np.zeros((H, W), bool))
res['hand_lower'] = complete_person('hand_lower', k=31)

# ---------------- neighbours with the jaw man gone ----------------
P = None
_a, _b = src[1260:1394, 140:258], src[1260:1394, 290:396]; _o = 20; _r = np.linspace(0, 1, _o)[None, :, None]
P = np.concatenate([_a[:, :-_o], _a[:, -_o:] * (1 - _r) + _b[:, :_o] * _r, _b[:, _o:]], 1)
pm = P.reshape(-1, 3).mean(0); o = 24; h, w = P.shape[:2]
ra = np.linspace(0, 1, o)[:, None, None]
T = P.copy(); T[:o] = P[:o] * ra + P[h - o:] * (1 - ra); T = T[:h - o]
ca = np.linspace(0, 1, o)[None, :, None]
T2 = T.copy(); T2[:, :o] = T[:, :o] * ca + T[:, w - o:] * (1 - ca); T = T2[:, :w - o]
yy, xx = np.mgrid[0:H, 0:W]
tex = T[yy % T.shape[0], xx % T.shape[1]]
hole = cv2.dilate(Mk['jaw'].astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~static_pic
bw = (blue & ~hole).astype(np.float32)
fillc = tex - pm + cv2.GaussianBlur(src * bw[..., None], (0, 0), 35) / (cv2.GaussianBlur(bw, (0, 0), 35)[..., None] + 1e-4)
face = src.copy(); face[hole] = fillc[hole]
face_added = np.zeros((H, W), bool)
# (1) the closed-eye lash tips that stayed on the cheek figure belong to the jaw man -> paper
tips = polym([(410, 714), (433, 714), (433, 733), (410, 733)]) & ~Mk['jaw'] & ~((R_ > B_ + 25) & (mean > 170)) & ~blue
face[tips] = fillc[tips]; face_added |= tips
# (2) the nose man's red loincloth: join the floating red piece to his bottom (cloth texture from the piece)
red_piece = polym([(236, 760), (380, 760), (380, 795), (236, 795)]) & static_pic
# drape: the red piece's own folded strip, stretched vertically and narrowed toward his hips
# drape = the red piece reflected upward across its own top edge, so the join is seamless and the
# drape is exactly as wide as the piece at the bottom; it tapers to his hips at the top
redm = (R_ > B_ + 62) & (mean > 120)
cols = np.arange(W); rtop = np.full(W, 776.); rbot = np.full(W, 782.)
for x in range(244, 373):
    yy = np.where(redm[760:800, x])[0] + 760
    if len(yy): rtop[x], rbot[x] = yy.min(), yy.max()
rtop = np.clip(cv2.GaussianBlur(rtop[None, :], (0, 0), 6)[0], 768, 778)
rbot = np.maximum(cv2.GaussianBlur(rbot[None, :], (0, 0), 3)[0], rtop + 5)
J = 777                                   # join row: covers the piece's dotted top line
CLOTH = [(292, 738), (312, 739), (336, 734), (346, 748), (360, 762), (373, 772), (373, J), (244, J), (252, 768), (270, 756), (284, 745)]
gap = polym(CLOTH) & (~static_pic | (yy_ >= 760))
gy, gx = np.where(gap)
yt = np.full(W, 10 ** 6); np.minimum.at(yt, gx, gy)
xl = np.full(H, 10 ** 6); xr = np.zeros(H, int); np.minimum.at(xl, gy, gx); np.maximum.at(xr, gy, gx)
u = (gx - xl[gy]) / np.maximum(1, xr[gy] - xl[gy])
sx_ = (244 + u * 128).astype(np.float32)
d = (J - gy) / np.maximum(1, J - yt[gx])                               # 0 at the join, 1 at the hips
sxi = np.clip(np.round(sx_).astype(int), 0, W - 1)
sy_ = (rtop[sxi] + 1.5 + d * (rbot[sxi] - rtop[sxi] - 3)).astype(np.float32)
mapx = np.zeros((H, W), np.float32); mapy = np.zeros((H, W), np.float32)
mapx[gy, gx] = sx_; mapy[gy, gx] = sy_
warped = cv2.remap(src, mapx, mapy, cv2.INTER_CUBIC)
# tone: the reflected piece, low-pass only (no stretched blobs); grain: the piece's own plain red pixels
ref = src[redm & polym([(244, 760), (373, 760), (373, 795), (244, 795)]) & (mean > 150)]
tone = cv2.GaussianBlur(warped, (0, 0), 4)[gy, gx]
tone = (tone - tone.mean(0)) * 0.6 + ref.mean(0)
rng = np.random.default_rng(11)
gr = np.zeros((H, W, 3), np.float32); gr[gy, gx] = ref[rng.integers(0, len(ref), len(gy))] - ref.mean(0)
gr = cv2.GaussianBlur(gr, (0, 0), 0.7)
vals = tone + gr[gy, gx] * 1.6
face[gy, gx] = np.clip(vals, 0, 255)
# the piece's fold lines continue up the drape as thin curves (print's ink), gathering at his waist
folds = np.zeros((H, W), np.float32)
for pts in [[(327, 778), (324, 768), (320, 756), (316, 744)],
            [(340, 778), (336, 766), (330, 752), (324, 741)],
            [(350, 778), (346, 767), (339, 754), (331, 740)],
            [(366, 777), (358, 767), (348, 754), (338, 740)],
            [(266, 779), (277, 767), (290, 755), (302, 744)]]:
    cv2.polylines(folds, [np.array(pts, np.int32)], False, 1.0, 1, cv2.LINE_AA)
folds = cv2.GaussianBlur(folds, (0, 0), 0.5) * gap * 0.85
face = face * (1 - folds[..., None]) + INK * folds[..., None]
face_added |= folds > 0.1
face_added |= gap
cloth = gap | red_piece
# ink on the two sides of the hanging cloth (smooth curves in the print's ink colour)
sides = np.zeros((H, W), np.uint8)
cv2.polylines(sides, [np.array([(284, 745), (270, 756), (256, 766), (245, 774)], np.int32)], False, 1, 2, cv2.LINE_AA)
cv2.polylines(sides, [np.array([(338, 736), (347, 748), (360, 761), (371, 771)], np.int32)], False, 1, 2, cv2.LINE_AA)
ends = (sides > 0) & (~static_pic | (yy_ >= 760))
ea = cv2.GaussianBlur(ends.astype(np.float32), (0, 0), 0.6)[..., None]
face = face * (1 - ea) + INK * ea; face_added |= ends
# (3) every neighbour's cut edge facing the hole gets the print's ink where it had none
nb = static_pic & ~gap
face, inked = ink_edge(face, nb.astype(np.float32), nb | gap, Mk['jaw'] & ~gap)
face_added |= inked

# ---------------- outputs ----------------
GREY = np.array([228., 228., 228.])
def on_grey(rgb, alpha, box):
    x0, y0, x1, y1 = box
    c = rgb * alpha[..., None] + GREY * (1 - alpha[..., None])
    return c[y0:y1, x0:x1]
def tint(img, added, box=None):
    t = img.copy(); t[added] = t[added] * 0.6 + np.array([255., 0, 255.]) * 0.4
    return t if box is None else t[box[1]:box[3], box[0]:box[2]]
BOX = {'jaw': (150, 600, 520, 960), 'hand_upper': (90, 930, 600, 1260), 'hand_lower': (90, 980, 580, 1360)}
pairs = []
for n in ['jaw', 'hand_upper', 'hand_lower']:
    rgb, al, added = res[n]
    after = on_grey(rgb, al, BOX[n]); before = on_grey(src, A[n], BOX[n])
    Image.fromarray(np.clip(after, 0, 255).astype(np.uint8)).save(OUT + '%s.png' % n)
    full_after = rgb * al[..., None] + GREY * (1 - al[..., None])
    pairs.append((n, before, after, tint(full_after, added, BOX[n])))
Image.fromarray(np.clip(face, 0, 255).astype(np.uint8)).save(OUT + 'face_without_jaw.png')
FB = (150, 560, 560, 960)
face_plain = src.copy(); face_plain[hole] = fillc[hole]            # v3 state: neighbours not completed
pairs.append(('face_without_jaw', face_plain[FB[1]:FB[3], FB[0]:FB[2]], face[FB[1]:FB[3], FB[0]:FB[2]], tint(face, face_added, FB)))
# overlay: whole print with each completed man shown at his place + the completed face, additions tinted
ov = face.copy()
for n in ['hand_lower', 'hand_upper']:
    rgb, al, added = res[n]
    ov = ov * (1 - al[..., None]) + rgb * al[..., None]
ov_t = tint(ov, face_added | res['hand_upper'][2] | res['hand_lower'][2])
jaw_rgb, jaw_al, jaw_add = res['jaw']
jt = tint(jaw_rgb * jaw_al[..., None] + GREY * (1 - jaw_al[..., None]), jaw_add)
# the jaw man is placed beside the print (he is away from the face in these frames)
canvas = np.full((H, W + 420, 3), 255.)
canvas[:, :W] = ov_t
canvas[300:300 + 360, W + 20:W + 20 + 370] = jt[600:960, 150:520]
ci = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(ci)
fnt = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 22)
d.text((W + 20, 260), 'jaw man (completed)', fill=(0, 0, 0), font=fnt)
d.text((W + 20, 680), 'magenta = added / copied', fill=(200, 0, 200), font=fnt)
ci.save(B + 'completion_overlay.png')
# contact sheet: before -> after -> after with additions tinted
rows = []
for n, b, a, t in pairs:
    hh = 330; sc = hh / b.shape[0]
    ims = [Image.fromarray(np.clip(x, 0, 255).astype(np.uint8)).resize((int(x.shape[1] * sc), hh), Image.LANCZOS) for x in (b, a, t)]
    row = Image.new('RGB', (sum(i.width for i in ims) + 40, hh + 34), 'white'); dd = ImageDraw.Draw(row)
    xo = 0
    for lab_, im in zip(['before', 'after', 'added (magenta)'], ims):
        row.paste(im, (xo, 34)); dd.text((xo + 4, 4), '%s - %s' % (n, lab_), fill=(0, 0, 0), font=fnt); xo += im.width + 20
    rows.append(row)
sw = max(r.width for r in rows); sh = sum(r.height for r in rows) + 10 * len(rows)
sheet = Image.new('RGB', (sw, sh), 'white'); y = 0
for r in rows: sheet.paste(r, (0, y)); y += r.height + 10
sheet.save(B + 'sheet.jpg', quality=90)
for n in res: print(n, 'added px', int(res[n][2].sum()))
print('face added px', int(face_added.sum()))
# hand-off to the GIF build
np.savez_compressed(OUT + 'layers_v4.npz',
    jaw_rgb=np.clip(res['jaw'][0], 0, 255).astype(np.uint8), jaw_a=res['jaw'][1].astype(np.float32), jaw_add=res['jaw'][2],
    lo_rgb=np.clip(res['hand_lower'][0], 0, 255).astype(np.uint8), lo_a=res['hand_lower'][1].astype(np.float32), lo_add=res['hand_lower'][2],
    up_a=A['hand_upper'].astype(np.float32), face=np.clip(face, 0, 255).astype(np.uint8), face_added=face_added)
