import trimesh, numpy as np, glob, os, sys, json, subprocess
from PIL import Image, ImageDraw
OLD = r'C:/Users/admin/Desktop/HEXA-Orange/scripts/upper_leg/checks'
SP = r'C:/Users/admin/Desktop/HEXA-Orange/scripts/upper_leg'
OUT = r'C:/Users/admin/Desktop/HEXA-Orange/output/v2'
sys.path.insert(0, OLD)
os.chdir(OLD)
from dmap import depthmap, MAPS
from scipy.spatial import cKDTree

files = sorted(glob.glob(OUT + '/Orange_UpperLeg_*/**/*.stl', recursive=True))
a = np.load('orig_maps.npz')
pk = json.load(open('pk.json'))
from shapely.geometry import Polygon
from shapely import contains_xy
HIP = Polygon(pk['hip']); KNEE = Polygon(pk['knee'])
tiles = []
for f in files:
    leg = f[-6:-4]
    m = trimesh.load(f)
    wt = m.is_watertight; parts = len(m.split(only_watertight=False))
    if leg in ('L2', 'R1'):
        T = np.eye(4); T[2, 2] = -1; m.apply_transform(T)   # back into the L1 frame
        m.invert() if m.volume < 0 else None
    # interface maps: pocket cores + holes
    worst = {}
    for k in ('hip_inner', 'knee_inner', 'hip_outer', 'knee_outer'):
        us, vs, d = depthmap(m, *MAPS[k])
        U, V = np.meshgrid(us, vs, indexing='ij')
        if k == 'hip_inner': mask = contains_xy(HIP.buffer(-0.15), U, V)
        elif k == 'knee_inner': mask = contains_xy(KNEE.buffer(-0.15), U, V)
        elif k == 'hip_outer': mask = (np.hypot(U - 1.52, V + 23.02) < 4) | (np.hypot(U - 1.52, V + 34.45) < 4)
        else: mask = (np.hypot(U - 15.23, V + 59.85) < 4) | (np.hypot(U - 15.23, V + 48.42) < 4)
        A = a[k][mask]; B = d[mask]; ok = ~np.isnan(A) & ~np.isnan(B)
        diff = np.abs(A[ok] - B[ok])
        worst[k] = (round(float(np.percentile(diff, 99.9)), 3), int((diff > 0.1).sum()))
    # thin walls (same method as thin.py)
    r = []
    print(os.path.relpath(f, OUT), '| watertight', wt, 'parts', parts, '| interface p99.9/count>0.1', worst, '|', ' / '.join(x.strip() for x in r))
    # label render: outer face depth map seen from +y (true view: image right = -x)
    xs = np.arange(-12.6, 8.0, 0.06); zs = np.arange(-47.3, -16.4, 0.06)
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    if leg in ('L2', 'R1'):
        Zq = -Z   # render the real part (mirrored) as it is, z up
    O = np.c_[X.ravel(), np.full(X.size, 45.0), Z.ravel()]
    mm = trimesh.load(f)
    zz = zs if leg not in ('L2', 'R1') else -zs[::-1]
    X, Z = np.meshgrid(xs, zz, indexing='ij')
    O = np.c_[X.ravel(), np.full(X.size, 45.0), Z.ravel()]
    loc, ir, _ = mm.ray.intersects_location(O, np.tile([0, -1, 0], (X.size, 1)), multiple_hits=False)
    y = np.full(X.size, np.nan); y[ir] = loc[:, 1]; y = y.reshape(X.shape)
    v = np.clip((39.36 - y) / 0.6, 0, 1); v[np.isnan(y)] = 1
    img = (255 * (1 - v)).astype(np.uint8).T[::-1, ::-1]   # rows: z top->bottom, cols: x from +x(left)... flipped so right = -x
    im = Image.fromarray(img).convert('RGB')
    ImageDraw.Draw(im).text((4, 4), os.path.basename(f)[:-4].replace('Orange_UpperLeg_', ''), fill=(255, 0, 0))
    tiles.append(im)
W = tiles[0].width; H = tiles[0].height
sheet = Image.new('RGB', (4 * (W + 8), 4 * (H + 8)), 'white')
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % 4) * (W + 8), (i // 4) * (H + 8)))
sheet = sheet.resize((sheet.width * 3 // 4, sheet.height * 3 // 4))
sheet.save(SP + '/labels_sheet.png'); print('sheet', sheet.size, len(tiles))
