"""Replay the Sesame robot walk (firmware/movement-sequences.h, runWalkPose) on the Orange assembly.

Angle mapping (assumption, confirm with the user):
  hips  : servo 90 = leg straight out sideways; +1 deg servo = +1 deg CCW seen from above (Stand splays legs to the corners)
  knees : Stand value (R4/L3 = 0, R3/L4 = 180) = lower leg straight down; 90 = lower leg horizontal (Rest pose)
"""
import numpy as np, json, trimesh, sys, itertools
SP = r'C:/Users/admin/Desktop/HEXA-Orange/scripts/walk'
ASM = r'C:/Users/admin/Desktop/HEXA-Orange/scripts/assembly'
A = ASM + '/asm/'
SUB = int(sys.argv[1]) if len(sys.argv) > 1 else 5      # interpolation steps per keyframe move

info = json.load(open(A + 'info.json'))
poses = json.load(open(ASM + '/poses.json'))
LEGS = ['L1', 'L2', 'R1', 'R2']
KNEE_OF = {'L1': 'L3', 'L2': 'L4', 'R1': 'R3', 'R2': 'R4'}
KNEE_STAND = {'R4': 0, 'R3': 180, 'L3': 0, 'L4': 180}
# MG90S occurrences were created per leg in order: hip, knee
SERVO = {'L1': ('MG90S_2', 'MG90S_3'), 'L2': ('MG90S_4', 'MG90S_5'), 'R1': ('MG90S_6', 'MG90S_7'), 'R2': ('MG90S_8', 'MG90S_9')}

def load(name):
    m = trimesh.load(A + name + '.stl')
    T = np.array(info[name]['T']).reshape(4, 4)
    T[:3, 3] *= 10.0                      # Fusion cm -> mm
    m.apply_transform(T)
    bb = np.array(info[name]['bbox'])
    # Fusion's occurrence box can be loose for rotated parts, so the mesh must sit inside it (and be close on most sides)
    inside = np.all(m.bounds[0] >= bb[0] - 0.6) and np.all(m.bounds[1] <= bb[1] + 0.6)
    close = (np.abs(m.bounds - bb) < 0.6).sum()
    assert inside and close >= 3, (name, m.bounds.round(2).tolist(), bb.tolist())
    return m

def rot_about(axis, point, deg):
    T = trimesh.transformations.rotation_matrix(np.radians(deg), axis, point)
    return T

# --- Sesame keyframes (servo angles) ---
STAND = dict(R1=135, R2=45, L1=45, L2=135, R4=0, R3=180, L3=0, L4=180)
def apply(state, **kw):
    s = dict(state); s.update(kw); return s
REST = {k: 90 for k in STAND}          # servos zeroed: legs straight out, lower legs horizontal
keys = [('rest (zero, all 90)', REST), ('stand', STAND)]
s = apply(STAND, R3=135, L3=45, R2=100, L1=25); keys.append(('init step', s))
LOOP = [dict(R3=135, L3=0), dict(L4=135, L2=90, R4=0, R1=180), dict(R2=45, L1=90),
        dict(R4=45, L4=180), dict(R3=180, L3=45, R2=90, L1=0), dict(L2=135, R1=90)]
for cyc in range(2):
    for k, step in enumerate(LOOP):
        s = apply(s, **step); keys.append(('cycle %d step %d' % (cyc + 1, k + 1), s))
keys.append(('stand', STAND))
keys.append(('rest (zero, all 90)', REST))

# --- geometry ---
parts = {}
for leg in LEGS:
    lo = poses[leg]['lower_name']
    parts[leg] = dict(up=load('UpperLeg_%s_1' % leg), low=load('LowerLeg_%s_1' % lo), hip=load(SERVO[leg][0]), knee=load(SERVO[leg][1]))
static = {n: load(n) for n in ('Base_wide_1', 'body_Top')}

geo = {}
for leg in LEGS:
    Tup = np.array(poses[leg]['upper'])
    s = 1 if leg in ('L1', 'R2') else -1           # L1-shaped parts: L1, R2
    hp = Tup @ np.r_[-7.37, 15.23, -59.85 * s, 1.0]      # hip pocket mouth, on the hip axis
    hip_pt = np.array([hp[0], hp[1], 0.0])
    kp = (Tup @ np.r_[1.52, 34.28, -23.02 * s, 1])[:3]
    kd = Tup[:3, :3] @ np.array([0, 1.0, 0])
    # knee sign: positive knee 'lift' must raise the foot and move it outward
    low = parts[leg]['low']; foot = low.vertices[np.argmin(low.vertices[:, 2])]
    # hanging straight down, both directions raise the foot: pick the one that swings it OUTWARD (toward Sesame's flat Rest pose)
    yc = -2.38
    moved = kp + rot_about(kd, kp, 10)[:3, :3] @ (foot - kp)
    sign = 1 if abs(moved[1] - yc) > abs(foot[1] - yc) else -1
    geo[leg] = dict(hip_pt=hip_pt, kp=kp, kd=kd, ksign=sign, foot=foot)

def leg_tf(leg, hip_deg, knee_deg):
    g = geo[leg]
    H = rot_about([0, 0, 1], g['hip_pt'], hip_deg)
    K = rot_about(g['kd'], g['kp'], g['ksign'] * knee_deg)
    return dict(up=H, low=H @ K, knee=H @ K)

def angles(state):
    out = {}
    for leg in LEGS:
        kn = KNEE_OF[leg]
        out[leg] = (state[leg] - 90.0, abs(state[kn] - KNEE_STAND[kn]))
    return out

frames = []
for (n0, a), (n1, b) in zip(keys[:-1], keys[1:]):
    for i in range(SUB):
        t = i / SUB
        st = {k: a[k] + (b[k] - a[k]) * t for k in a}
        frames.append((n1 if i == SUB - 1 else n0 + ' -> ' + n1, st))
frames.append((keys[-1][0], keys[-1][1]))

def inter_vol(m1, m2):
    if not (np.all(m1.bounds[0] <= m2.bounds[1]) and np.all(m2.bounds[0] <= m1.bounds[1])):
        return 0.0
    try:
        r = trimesh.boolean.intersection([m1, m2], engine='manifold')
        return float(r.volume) if len(r.faces) else 0.0
    except Exception:
        return -1.0

report = []
out_frames = []
for fi, (label, st) in enumerate(frames):
    ang = angles(st)
    moved = {}
    tfs = {}
    for leg in LEGS:
        T = leg_tf(leg, *ang[leg])
        tfs[leg] = {k: v.tolist() for k, v in T.items()}
        for part in ('up', 'low', 'knee'):
            m = parts[leg][part].copy(); m.apply_transform(T[part]); moved[(leg, part)] = m
    hits = []
    # moving parts vs body (base + shell) and vs the static hip servos
    for (leg, part), m in moved.items():
        for sn, sm in static.items():
            v = inter_vol(m, sm)
            if v > 0.5: hits.append(('%s %s' % (leg, part), sn, round(v, 1)))
        for leg2 in LEGS:
            if leg2 == leg and part != 'up': continue
            v = inter_vol(m, parts[leg2]['hip'])
            if v > 0.5 and not (leg2 == leg and part == 'up'): hits.append(('%s %s' % (leg, part), '%s hip servo' % leg2, round(v, 1)))
    # legs vs other legs
    for (l1, p1), (l2, p2) in itertools.combinations(moved, 2):
        if l1 == l2: continue
        v = inter_vol(moved[(l1, p1)], moved[(l2, p2)])
        if v > 0.5: hits.append(('%s %s' % (l1, p1), '%s %s' % (l2, p2), round(v, 1)))
    # upper leg vs its own lower leg (knee bend)
    for leg in LEGS:
        v = inter_vol(moved[(leg, 'up')], moved[(leg, 'low')])
        if v > 0.5: hits.append(('%s upper' % leg, '%s lower' % leg, round(v, 1)))
    feet = {leg: float(moved[(leg, 'low')].bounds[0][2]) for leg in LEGS}
    report.append(dict(frame=fi, label=label, angles={k: [round(v[0], 1), round(v[1], 1)] for k, v in ang.items()}, hits=hits,
                       feet=[round(feet[l], 1) for l in LEGS]))
    out_frames.append(dict(label=label, servo={k: round(v, 1) for k, v in st.items()}, tfs=tfs))
    if hits or label.startswith('cycle 1') or fi == 0:
        print('%3d %-34s hips/knees %s  feet z %s  %s' % (fi, label[:34], {k: tuple(v) for k, v in report[-1]['angles'].items()}, report[-1]['feet'], hits if hits else 'no clash'))
json.dump(dict(names={leg: dict(up='UpperLeg_%s:1' % leg, low='LowerLeg_%s:1' % poses[leg]['lower_name'], knee=SERVO[leg][1].replace('_', ':')) for leg in LEGS},
               frames=out_frames), open(SP + '/gait_frames.json', 'w'))
json.dump(report, open(SP + '/gait_report.json', 'w'), indent=1)
n_hit = sum(1 for r in report if r['hits'])
print('frames', len(report), 'frames with a clash', n_hit, ' knee signs', {l: geo[l]['ksign'] for l in LEGS})
