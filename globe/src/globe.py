import numpy as np
from PIL import Image
import os
G = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SF = 4
TEX = np.asarray(Image.open(f'{G}/dl/R0000004-4.jpg').convert('RGB')).astype(np.float32)
# gentle levels + saturation on the map texture (ink and hand-colouring a touch richer)
SAT, BLACK = 1.30, 18.0
_l = TEX.mean(axis=2, keepdims=True)
TEX = _l + (TEX - _l) * SAT
TEX = np.clip((TEX - BLACK) * 255.0 / (255.0 - BLACK), 0, 255)
# calm the paper grain (edge-preserving smoothing) so the GIF compresses; lines stay sharp
import cv2, os
if os.environ.get('SMOOTH', '1') == '1':
    TEX = cv2.bilateralFilter(TEX.astype(np.uint8), 7, 22, 4).astype(np.float32)
# disk centres / map radius in sf4 pixels (fitted on sf8 then x2)
WEST = (1290, 1488, 1100, -110.0)
EAST = (3558, 1452, 1100, 70.0)

def sample(px, py):
    h, w, _ = TEX.shape
    px = np.clip(px, 0, w-1.001); py = np.clip(py, 0, h-1.001)
    x0 = px.astype(int); y0 = py.astype(int); fx = (px-x0)[...,None]; fy = (py-y0)[...,None]
    a = TEX[y0, x0]; b = TEX[y0, x0+1]; c = TEX[y0+1, x0]; d = TEX[y0+1, x0+1]
    return (a*(1-fx)+b*fx)*(1-fy) + (c*(1-fx)+d*fx)*fy

def render(lon0, lat0, size, R, cx=None, cy=None, shade=True, squash=(1.0, 1.0)):
    """Orthographic view; globe radius R px centred at (cx,cy) in a size=(W,H) canvas.
    Returns RGB float array and alpha mask."""
    W, H = size
    cx = W/2 if cx is None else cx; cy = H/2 if cy is None else cy
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x = (xx + 0.5 - cx) / (R*squash[0]); y = -(yy + 0.5 - cy) / (R*squash[1])
    r2 = x*x + y*y
    inside = r2 < 1.0
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    # rotate: view centre (lon0, lat0)
    p0 = np.radians(lat0); l0 = np.radians(lon0)
    lat = np.arcsin(np.clip(z*np.sin(p0) + y*np.cos(p0), -1, 1))
    lon = l0 + np.arctan2(x, z*np.cos(p0) - y*np.sin(p0))
    lond = (np.degrees(lon) + 180) % 360 - 180
    out = np.zeros((H, W, 3), np.float32)
    east = ((lond - 70 + 540) % 360 - 180) ** 2 <= 90**2
    for disk, mask in ((EAST, east), (WEST, ~east)):
        dcx, dcy, dR, dl = disk
        d = np.radians(((lond - dl + 540) % 360) - 180)
        cl = np.cos(lat)
        k = 1.0 / (1.0 + cl*np.cos(d))
        X = cl*np.sin(d)*k; Y = np.sin(lat)*k
        m = mask & inside
        out[m] = sample(dcx + X[m]*dR, dcy - Y[m]*dR)
    if shade:
        # gentle sphere shading: light from upper left, keep the paper colour
        L = np.array([-0.45, 0.5, 0.74]); L /= np.linalg.norm(L)
        ndl = np.clip(x*L[0] + y*L[1] + z*L[2], 0, 1)
        f = (0.90 + 0.13*ndl) * (0.80 + 0.20*np.sqrt(z))
        f = f + 0.03*np.clip(ndl, 0, 1)**30
        out = out * f[..., None]
    alpha = np.clip((1 - np.sqrt(r2)) * R*min(squash) , 0, 1)
    return np.clip(out, 0, 255), alpha
