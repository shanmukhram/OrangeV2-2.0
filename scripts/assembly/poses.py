"""Standing-pose transforms for the full Orange assembly (mm, base frame: +X front, +Y left, +Z up).

Upper leg (L1 frame): the multi-hole knee PANEL pocket (axis along x at y 15.23, z -59.85, mouth x=-7.37,
pocket goes toward -x) sits on the BODY hip servo; the LABELLED plate pocket (axis along y at x 1.52,
z -23.02, mouth y=34.28, pocket goes toward +y) takes the LOWER-LEG servo.  (User, 2026-11-06.)
L2-shaped parts are the same with z -> -z.
"""
import numpy as np, json, trimesh, sys
SP = r'C:/Users/admin/Desktop/HEXA-Orange/scripts/assembly'
OUT = r'C:/Users/admin/Desktop/HEXA-Orange/output/v2'

DECK = 21.97                 # bracket post tops (servo tabs rest here)
TAB_BOT_BELOW_TOP = 8.26     # servo top face -> tab underside
MOUTH_ABOVE_TOP = 2.87       # servo top face -> horn pocket mouth
SERVO_TOP = DECK + TAB_BOT_BELOW_TOP
MOUTH = SERVO_TOP + MOUTH_ABOVE_TOP
SPLAY = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0   # deg the foot leans outward

def M(R, t):
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = t; return T

def basis(xw, yw, zw):
    R = np.array([xw, yw, zw], float).T
    assert abs(np.linalg.det(R) - 1) < 1e-9, R
    return R

def rot(axis, deg, center):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    if axis == 'y': R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    else: R = np.array([[1, 0, 0], [0, c, -s], [0, s, c]]) if axis == 'x' else np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    p = np.array(center, float); return M(R, p - R @ p)

X, Y, Z = np.eye(3)
# corner: (part shape, hip shaft XY, outward world dir); 1 = rear, 2 = front, L = -Y side, R = +Y side
LEGS = {
    'L1': ('L1', (-28.98, -34.78), -Y),
    'L2': ('L2', (80.40, -34.78), -Y),
    'R1': ('L2', (-28.98, 30.02), Y),
    'R2': ('L1', (80.40, 30.02), Y),
}
LOWER = {'L1': 'L3', 'L2': 'L4', 'R1': 'R3', 'R2': 'R4'}

ll = trimesh.load(OUT + '/Orange_LowerLeg_v2.stl')
# lower-leg servo in the LL frame: shaft along -x_LL, top face x=-21.2, shaft axis (y 28.04, z 51.57)
LL_SHAFT = np.array([-21.2 - MOUTH_ABOVE_TOP, 28.04, 51.57])   # where the plate's pocket mouth must be
R0 = basis(-Y, X, Z)          # LL x -> -y (shaft goes +y into the plate pocket), LL y -> x, LL z -> z
R_FLIP = rot('z', 180, (-8.18, 28.04, 0))   # turn the lower leg over about its length axis (servo stays put)
T_KS_LL = M(basis([0, 0, 1], [0, 1, 0], [-1, 0, 0]), [-21.2, 28.04, 51.57])

res = {}
for leg, (shape, (hx, hy), outw) in LEGS.items():
    s = 1 if shape == 'L1' else -1
    hip_z, knee_z = -59.85 * s, -23.02 * s
    # upper leg: x -> -Z (panel pocket opens downward onto the hip horn), leg runs from hip (z=hip_z) to knee
    zdir = outw * s                      # L1: +z points outward; L2 (mirrored): -z points outward
    xdir = -Z
    ydir = np.cross(zdir, xdir)
    R = basis(xdir, ydir, zdir)
    t = np.array([hx, hy, MOUTH]) - R @ np.array([-7.37, 15.23, hip_z])
    T_up = M(R, t)
    # lower leg into the upper-leg frame (pocket mouth at y = 34.28 on the labelled plate)
    T_ll = M(R0, np.array([1.52, 34.28, knee_z]) - R0 @ LL_SHAFT)
    best = None
    for flip in (False, True):
        T_b = T_ll @ R_FLIP if flip else T_ll
        pts = trimesh.transform_points(ll.vertices, T_b)
        d = pts - np.array([1.52, 0, knee_z]); far = pts[np.argmax(np.hypot(d[:, 0], d[:, 2]))]
        v = far - np.array([1.52, 0, knee_z])
        psi = np.degrees(np.arctan2(v[2], v[0]))           # angle in the (x, z) plane from +x (= world down)
        # target: straight down, optionally splayed outward (outward in local z is sign of zdir.outw)
        tgt = np.degrees(np.arctan2(np.sign(zdir @ outw) * np.sin(np.radians(SPLAY)), np.cos(np.radians(SPLAY))))
        T_knee = rot('y', psi - tgt, (1.52, 0, knee_z))
        T_low = T_up @ T_knee @ T_b
        shield = T_low[:3, :3] @ np.array([0, 1, 0])        # shield faces +y in the LL frame
        tip = (T_up @ T_knee @ np.r_[far, 1])[:3]
        ok = shield @ outw > 0.5
        if ok: best = (flip, T_knee, T_low, tip, shield)
    flip, T_knee, T_low, tip, shield = best
    T_ks = T_up @ T_knee @ T_ll @ T_KS_LL
    sx = 1 if hx > 30 else -1
    T_hs = M(basis(sx * X, sx * Y, Z), [hx, hy, SERVO_TOP])
    for nm, T in (('lower', T_low), ('knee_servo', T_ks), ('upper', T_up), ('hip', T_hs)):
        assert abs(np.linalg.det(T[:3, :3]) - 1) < 1e-6, (leg, nm)
    res[leg] = dict(upper=T_up.tolist(), lower=T_low.tolist(), hip_servo=T_hs.tolist(), knee_servo=T_ks.tolist(),
                    lower_name=LOWER[leg], flipped=flip, foot=[round(float(v), 2) for v in tip])
    kneew = (T_up @ np.r_[1.52, 34.28, knee_z, 1])[:3]
    print(leg, 'flipped', flip, 'knee pocket mouth', np.round(kneew, 1), 'foot', np.round(tip, 1), 'shield dir', np.round(shield, 2))
json.dump(res, open(SP + '/poses.json', 'w'), indent=1)
