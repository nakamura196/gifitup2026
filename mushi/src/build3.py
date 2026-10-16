"""Utsusemi: cicada leaves, a new one climbs out of the nymph shell and becomes the drawing again.
Source: Kurimoto Tanshu, Senchufu vol.[2], NDL pid 2576062, canvas 83 (PDM).
Usage: python3 build.py <agentdir>
"""
import sys, math, os, subprocess
import numpy as np, cv2

D = sys.argv[1]
src = cv2.imread(os.environ.get('DL', f'{D}/dl') + '/p83.jpg').astype(np.float32)
mA = cv2.imread(f'{D}/work/m_adult.png', 0)
mN = cv2.imread(f'{D}/work/m_nymph.png', 0)

CROP = tuple(int(v) for v in os.environ.get('CROP', '280,330,2600,1900').split(','))
OUTW = int(os.environ.get('OUTW', '720'))
S = 0.5  # working scale relative to 2800px source

# ---- clean plate (adult removed) -------------------------------------------------
hole = cv2.dilate(mA, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51)))
src8 = np.clip(src, 0, 255).astype(np.uint8)
plate = cv2.inpaint(src8, hole, 9, cv2.INPAINT_TELEA).astype(np.float32)
# keep only low frequencies of the inpaint inside the hole (no smeared streaks)
low = cv2.GaussianBlur(plate, (0, 0), 30)
hb = cv2.GaussianBlur(hole.astype(np.float32) / 255, (0, 0), 6)[..., None]
plate = src * (1 - hb) + low * hb
# re-add paper grain: copy grain (high-pass) from a blank paper patch nearby
rng = np.random.default_rng(1)
grainsrc = src[1650:1815, 760:1260]  # empty paper below the adult (source coords)
hp = grainsrc - cv2.GaussianBlur(grainsrc, (0, 0), 6)
ys, xs = np.nonzero(hole)
y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
tile = np.tile(hp, (int(np.ceil((y1 - y0) / hp.shape[0])) + 1, int(np.ceil((x1 - x0) / hp.shape[1])) + 1, 1))
g = tile[:y1 - y0, :x1 - x0]
hm = cv2.GaussianBlur(hole.astype(np.float32) / 255, (0, 0), 4)[y0:y1, x0:x1, None]
plate[y0:y1, x0:x1] += g * hm

def to_work(img):
    x0, y0, x1, y1 = CROP
    c = img[y0:y1, x0:x1]
    return cv2.resize(c, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)

P0 = to_work(src)        # original
PL = to_work(plate)      # adult removed
H, W = P0.shape[:2]

def sprite(mask, feather=5):
    """RGBA sprite (in work scale) cut from source, with soft paper margin."""
    m = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    m = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), feather)
    ys, xs = np.nonzero(m > 0.01)
    by0, by1, bx0, bx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgb = src[by0:by1, bx0:bx1]
    a = m[by0:by1, bx0:bx1]
    rgb = cv2.resize(rgb, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)
    a = cv2.resize(a, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)
    # origin of sprite in work coords
    ox = (bx0 - CROP[0]) * S
    oy = (by0 - CROP[1]) * S
    return rgb, a, (ox, oy)

A_rgb, A_a, A_o = sprite(mA)
N_rgb, N_a, N_o = sprite(mN)

# key points (source coords -> work coords)
def w(pt):
    return ((pt[0] - CROP[0]) * S, (pt[1] - CROP[1]) * S)
A_head_src, A_tail_src = (950, 1390), (1200, 1445)
A_hinge = w((1030, 1400))       # where wings attach
A_center = w((1080, 1420))
N_center = w((615, 1555))
N_back = w((606, 1530))          # middle of the thorax split line
A_angle = math.degrees(math.atan2(A_head_src[1] - A_tail_src[1], A_head_src[0] - A_tail_src[0]))  # ~192
N_angle = math.degrees(math.atan2(1575 - 1492, 590 - 620))  # nymph faces down-left (~110)

# body vs wings split for the adult sprite (body = ellipse along axis + head side)
bh, bw = A_a.shape
yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
cxs, cys = A_center[0] - A_o[0], A_center[1] - A_o[1]
ang = math.radians(A_angle)
ux, uy = math.cos(ang), math.sin(ang)
dx, dy = xx - cxs, yy - cys
along = dx * ux + dy * uy
across = -dx * uy + dy * ux
body = ((along / (150 * S)) ** 2 + (across / (62 * S)) ** 2) <= 1.0
body |= along > 85 * S  # head + front legs region
body_f = cv2.GaussianBlur(body.astype(np.float32), (0, 0), 3)
A_body_a = A_a * body_f
A_wing_a = A_a * (1 - body_f)
hx, hy = A_hinge[0] - A_o[0], A_hinge[1] - A_o[1]

def warp(rgb, a, M, out_hw):
    r = cv2.warpAffine(rgb, M, (out_hw[1], out_hw[0]), flags=cv2.INTER_LINEAR, borderValue=0)
    al = cv2.warpAffine(a, M, (out_hw[1], out_hw[0]), flags=cv2.INTER_LINEAR, borderValue=0)
    return r, al

def over(base, rgb, a):
    return base * (1 - a[..., None]) + rgb * a[..., None]

# ======================= v2 animation =======================
# pale (teneral) version of the adult that keeps the ink linework
Lsp = cv2.cvtColor(np.clip(A_rgb, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
lines = np.clip(cv2.GaussianBlur(Lsp, (0, 0), 2.5) - Lsp, 0, 255)          # local dark strokes
TINT = np.array([0.86, 0.96, 0.93], np.float32)                               # BGR multiplier: pale cream-green
A_pale = (255 - (255 - A_rgb) * 0.38) * TINT
A_pale = A_pale - lines[..., None] * 1.0 - np.clip(150 - Lsp, 0, 255)[..., None] * 0.22
A_pale = np.clip(A_pale, 0, 255)

# nymph ink colour (darkest strokes) for the ecdysial crack
nm = N_a > 0.9
nl = cv2.cvtColor(np.clip(N_rgb, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
INK = np.median(N_rgb[nm & (nl < np.percentile(nl[nm], 4))], axis=0)
CRACK = (w((621, 1490)), w((588, 1578)))   # along the drawn mid-thorax line

PIVOT = 26.0   # thorax/abdomen junction, sprite units (work px) ahead of the sprite centre along the body axis

def adult_layer(pos, angle, scale, wing_along, wing_across, pale, stretch=1.0, reveal=None,
                fore=1.0, bend=0.0, front_lim=None, back_lim=None, pivot_at=None, fold=None):
    """fore/bend: piecewise warp of the front segment (head+thorax) about the junction;
    front_lim: only body parts behind this along-axis limit are shown (head end still inside the shell);
    pivot_at: place the junction (instead of the centre) at this world point."""
    rgb = A_rgb * (1 - pale) + A_pale * pale if pale > 0 else A_rgb
    ca, sa = math.cos(ang), math.sin(ang)
    R = np.array([[ca, sa], [-sa, ca]])
    Mw2 = R.T @ np.diag([wing_along, wing_across]) @ R
    tw = np.array([hx, hy]) - Mw2 @ np.array([hx, hy])
    Mw = np.hstack([Mw2, tw[:, None]]).astype(np.float32)
    wr, wa = warp(rgb, A_wing_a, Mw, A_a.shape)
    if wing_along < 0.8 or pale > 0:   # crumpled / fresh wings are translucent
        wa = wa * (1 - 0.3 * pale)
    ba = A_body_a * (1 - wa)
    comp_rgb = wr * wa[..., None] + rgb * ba[..., None]
    comp_a = np.clip(wa + ba, 0, 1)
    if front_lim is not None:
        comp_a = comp_a * np.clip((front_lim - along) / 3.0, 0, 1)
    if back_lim is not None:
        comp_a = comp_a * np.clip((along - back_lim) / 3.0, 0, 1)
    if fore != 1.0 or bend != 0.0:
        FP = PIVOT if fold is None else fold
        Pp = np.array([cxs, cys]) + np.array([ux, uy]) * FP
        b_ = math.radians(bend)
        Rb = np.array([[math.cos(b_), -math.sin(b_)], [math.sin(b_), math.cos(b_)]])
        fore_ = math.copysign(max(abs(fore), 0.06), fore if fore != 0 else 1.0)
        Mf2 = Rb @ R.T @ np.diag([fore_, 1.0]) @ R
        tf = Pp - Mf2 @ Pp
        Mf = np.hstack([Mf2, tf[:, None]]).astype(np.float32)
        wf = np.clip((along - FP) / 8.0 + 0.5, 0, 1)
        fr_rgb, fr_a = warp(comp_rgb * (comp_a * wf)[..., None], comp_a * wf, Mf, A_a.shape)
        bk_a = comp_a * (1 - wf)
        bk_vis = bk_a * (1 - fr_a)            # folded front lies over the rest of the body
        acc = fr_rgb + comp_rgb * bk_vis[..., None]
        comp_a = np.clip(fr_a + bk_vis, 0, 1)
        comp_rgb = acc
    else:
        comp_rgb = comp_rgb * comp_a[..., None]
    comp_rgb = comp_rgb / np.maximum(comp_a[..., None], 1e-4)
    St2 = R.T @ np.diag([stretch, 1.0]) @ R
    rot = math.radians(angle - A_angle)
    Rr = np.array([[math.cos(rot), -math.sin(rot)], [math.sin(rot), math.cos(rot)]])
    M2 = scale * Rr @ St2
    if pivot_at is not None:
        pos = np.array(pivot_at) - M2 @ (np.array([ux, uy]) * PIVOT)
    t = np.array(pos) - M2 @ np.array([cxs, cys])
    M = np.hstack([M2, t[:, None]]).astype(np.float32)
    r, al = warp(comp_rgb, comp_a, M, (H, W))
    if reveal is not None:
        al = al * reveal
    return r, al

def place_of_pivot(pivot_world, angle, scale):
    rot = math.radians(angle - A_angle)
    Rr = np.array([[math.cos(rot), -math.sin(rot)], [math.sin(rot), math.cos(rot)]])
    return np.array(pivot_world) - scale * Rr @ (np.array([ux, uy]) * PIVOT)

def nymph_layer(rot=0.0, crack=0.0, gape=0.0):
    cx, cy = N_center[0] - N_o[0], N_center[1] - N_o[1]
    rgb = N_rgb.copy()
    if crack > 0:
        (x0, y0), (x1, y1) = CRACK
        # crack grows from the thorax middle outward
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        hx0, hy0 = mx + (x0 - mx) * crack - N_o[0], my + (y0 - my) * crack - N_o[1]
        hx1, hy1 = mx + (x1 - mx) * crack - N_o[0], my + (y1 - my) * crack - N_o[1]
        layer = np.zeros(rgb.shape[:2], np.float32)
        th = 2 + int(round(gape * 3))  # in 1/4-px units via shift? no: pixels
        th = 1 + int(round(gape * 1.5))
        cv2.line(layer, (int(hx0 * 4), int(hy0 * 4)), (int(hx1 * 4), int(hy1 * 4)), 1.0, th, cv2.LINE_AA, shift=2)
        layer = cv2.GaussianBlur(layer, (0, 0), 0.6)
        rgb = rgb * (1 - layer[..., None]) + INK * layer[..., None]
    M = cv2.getRotationMatrix2D((cx, cy), rot, 1.0)
    M[0, 2] += N_o[0]
    M[1, 2] += N_o[1]
    return warp(rgb, N_a, M, (H, W))

def ease(t):
    t = min(max(t, 0), 1)
    return t * t * (3 - 2 * t)

def lerp(a, b, t):
    return a + (b - a) * t

def bez(p, t):
    (a, b, c, d) = [np.array(q, float) for q in p]
    return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d

def angdiff(a, b):
    return ((b - a + 540) % 360) - 180

# flight path (work coords): forward-left lift, curve up, bank right, out of the top edge
P0 = np.array(A_center)
FLY_PATH = (P0, P0 + np.array([-90, -25]), P0 + np.array([-70, -230]), np.array([P0[0] + 260, -170]))

F_HOLD, F_CROUCH, F_FLY, F_PAUSE, F_CRACK, F_EMERGE, F_WALK, F_SET = 9, 5, 16, 3, 8, 28, 16, 5
total = F_HOLD + F_CROUCH + F_FLY + F_PAUSE + F_CRACK + F_EMERGE + F_WALK + F_SET
yy2, xx2 = np.mgrid[0:H, 0:W].astype(np.float32)
P0img = to_work(src)
frames = []

def flight_sample(tf):
    """tf = time in frames since launch (float). returns pos, heading, scale, flap"""
    u = min(max(tf / F_FLY, 0), 1)
    e = u ** 1.6
    pos = bez(FLY_PATH, e)
    d = bez(FLY_PATH, min(e + 0.02, 1)) - bez(FLY_PATH, max(e - 0.02, 0))
    tang = math.degrees(math.atan2(d[1], d[0]))
    head = A_angle + angdiff(A_angle, tang) * ease(u / 0.35)
    # wobble across the path and a little roll
    nrm = np.array([-math.sin(math.radians(tang)), math.cos(math.radians(tang))])
    wob = math.sin(tf * 2.3) * 3.0 * min(1, u * 4)
    pos = pos + nrm * wob
    head += math.sin(tf * 1.7 + 0.5) * 5 * min(1, u * 4)
    sc = 1.0 + 0.12 * ease(u / 0.3) - 0.32 * ease((u - 0.3) / 0.7)
    flap = 0.65 + 0.35 * math.cos(math.pi * tf * 1.0)    # alternates every frame
    return pos, head, sc, flap

for f in range(total):
    t = f
    if t < F_HOLD:
        frames.append(P0img.copy()); continue
    t -= F_HOLD
    base = PL.copy()
    nr, na = nymph_layer()
    base = over(base, nr, na)
    if t < F_CROUCH:
        u = t / (F_CROUCH - 1)
        c = math.sin(u * math.pi * 0.5)  # press down
        pos = (A_center[0] + 1.5 * c, A_center[1] + 2.5 * c)
        r, al = adult_layer(pos, A_angle + 2 * math.sin(t * 2.5), 1.0 - 0.03 * c, 1.0, 1.0 + 0.10 * c, 0)
        frames.append(over(base, r, al)); continue
    t -= F_CROUCH
    if t < F_FLY:
        # motion blur: average 3 sub-frame renders (premultiplied)
        acc_rgb = np.zeros((H, W, 3), np.float32); acc_a = np.zeros((H, W), np.float32)
        for s in (-0.33, 0.0, 0.33):
            tf = max(t + s, 0)
            pos, head, sc, flap = flight_sample(tf)
            if t == 0 and s <= 0:
                flap = 1.0
            r, al = adult_layer(tuple(pos), head, sc, 1.0, flap, 0)
            acc_rgb += r * al[..., None]; acc_a += al
        acc_rgb /= 3; acc_a /= 3
        fr = base * (1 - acc_a[..., None]) + acc_rgb
        frames.append(fr); continue
    t -= F_FLY
    if t < F_PAUSE:
        frames.append(base); continue
    t -= F_PAUSE
    if t < F_CRACK:
        u = t / (F_CRACK - 1)
        jit = math.sin(t * 2.6) * 2.0
        nr, na = nymph_layer(jit, crack=ease(u * 1.4), gape=ease((u - 0.5) / 0.5))
        frames.append(over(PL.copy(), nr, na)); continue
    t -= F_CRACK
    nr, na = nymph_layer(0, crack=1.0, gape=1.0)
    base = over(PL.copy(), nr, na)
    # emergence geometry in the nymph's frame
    nang = math.radians(N_angle)
    fwd = np.array([math.cos(nang), math.sin(nang)])     # towards nymph head
    split = np.array(N_back)
    # emergence frame: everything along the nymph's own head-tail axis (fwd = towards its head)
    ox, oy = xx2 - split[0], yy2 - split[1]
    alw = ox * fwd[0] + oy * fwd[1]          # along the back midline
    acw = -ox * fwd[1] + oy * fwd[0]         # across it
    SC = 0.80
    SLIDE = 70.0                              # abdomen length (work px) pulled out forward
    E_BULGE, E_WIDEN, E_LEAN, E_HANG, E_BEND, E_PULL = 8, 2, 5, 6, 3, 4   # = F_EMERGE frames
    THW = 24.0                                # half-width of the adult's thorax (work px)
    if t < F_EMERGE:
        k = t
        pv = split - fwd * 10 * S          # thorax sits over the slit
        FOLD = PIVOT - 30                   # bend point: behind the wing bases, so a long front part folds back
        hang_pv = pv + fwd * (30 * SC * 1.08) * 0.6   # fold point near the slit while hanging
        if k < E_BULGE + E_WIDEN:
            # 1) a lengthwise sliver along the crack: grows first in LENGTH, width stays narrow;
            #    the adult pushes forward along the axis so head, thorax and wing bases show
            if k < E_BULGE:
                u = ease((k + 1) / E_BULGE)
                L = lerp(14, 62, u)
                Wd = lerp(1.5, THW * 0.38, u * u)
            else:
                u = ease((k - E_BULGE + 1) / E_WIDEN)
                L = lerp(62, 75, u)
                Wd = lerp(THW * 0.38, THW * 1.3, u)
            push = lerp(0, 10, ease((k + 1) / (E_BULGE + E_WIDEN)))
            lens = np.clip((1 - (alw / L) ** 2 - (acw / Wd) ** 2) * 6, 0, 1)
            r, al = adult_layer(None, N_angle, SC, 0.38, 0.55, 1.0, stretch=1.08,
                                back_lim=PIVOT - 4 - 28 * ease((k + 1) / (E_BULGE + E_WIDEN)),
                                pivot_at=pv + fwd * push, reveal=lens)
        elif k < E_BULGE + E_WIDEN + E_LEAN + E_HANG:
            # 2) leans back towards the shell's tail (front half folds over), 3) hangs, body reaching past the tail
            j = k - E_BULGE - E_WIDEN
            if j < E_LEAN:
                fore = [0.9, 0.7, -0.7, -0.95, -1.08][j]   # skip the edge-on moment
                p = ease((j + 1) / E_LEAN)
            else:
                fore = -1.08 + 0.05 * math.sin((j - E_LEAN) * 0.9)
                p = 1.0
            pvv = (pv + fwd * 10) * (1 - p) + hang_pv * p
            r, al = adult_layer(None, N_angle, SC, 0.38, 0.55, 1.0, fore=fore, stretch=1.08,
                                back_lim=FOLD - 2, pivot_at=pvv, fold=FOLD)
        else:
            # 4) bends forward again, grips, pulls the abdomen out of the slit (moving forward along the axis)
            j = k - E_BULGE - E_WIDEN - E_LEAN - E_HANG
            if j < E_BEND:
                fore = [-0.6, 0.7, 0.95][j]
                p = ease((j + 1) / E_BEND)
                pvv = hang_pv * (1 - p) + pv * p
                sl = 0.0
            else:
                fore = 1.0
                sl = ease((j - E_BEND + 1) / E_PULL)
                pvv = pv + fwd * SLIDE * sl
            r, al = adult_layer(None, N_angle, SC, 0.38, 0.55, 1.0, fore=fore, stretch=lerp(1.08, 1.0, sl),
                                back_lim=(FOLD - 2 - SLIDE / SC * sl * 1.2) if sl < 1 else None,
                                pivot_at=pvv, fold=FOLD)
        frames.append(over(base, r, al)); continue
    t -= F_EMERGE
    if t < F_WALK:
        u = t / (F_WALK - 1)
        e = ease(u)
        start = place_of_pivot(split - fwd * 10 * S + fwd * SLIDE, N_angle, SC)
        mid = np.array([lerp(start[0], A_center[0], 0.5), min(start[1], A_center[1]) - 40 * S])
        p1 = start + (mid - start) * e
        p2 = mid + (np.array(A_center) - mid) * e
        pos = p1 + (p2 - p1) * e
        pos = (pos[0], pos[1] + math.sin(u * math.pi * 6) * 1.5 * S * (1 - e))
        head = N_angle + angdiff(N_angle, A_angle) * ease(u * 1.2)
        sc = lerp(SC, 1.0, ease(u * 1.1))
        wa_ = lerp(0.38, 1.0, ease((u - 0.1) / 0.8))
        wc_ = lerp(0.55, 1.0, ease((u - 0.1) / 0.7))
        pale = 1.0 - ease((u - 0.3) / 0.7)
        r, al = adult_layer(tuple(pos), head, sc, wa_, wc_, pale)
        frames.append(over(base, r, al)); continue
    t -= F_WALK
    u = (t + 1) / F_SET
    r, al = adult_layer(A_center, A_angle, 1.0, 1.0, 1.0, 0)
    nr, na = nymph_layer(0, crack=1.0, gape=1.0 - u)
    fr = over(over(PL.copy(), nr, na), r, al)
    frames.append(fr * (1 - u) + P0img * u)

OUT = os.environ.get('FRAMES', f'{D}/frames')
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(f'{OUT}/{f}')
OH = int(round(H * OUTW / W))
for i, fr in enumerate(frames):
    o = cv2.resize(np.clip(fr, 0, 255).astype(np.uint8), (OUTW, OH), interpolation=cv2.INTER_AREA)
    cv2.imwrite(f'{OUT}/f{i:03d}.png', o)
print('frames', len(frames), 'size', OUTW, OH, 'segments', dict(hold=F_HOLD, crouch=F_CROUCH, fly=F_FLY, pause=F_PAUSE, crack=F_CRACK, emerge=F_EMERGE, walk=F_WALK, set=F_SET))
