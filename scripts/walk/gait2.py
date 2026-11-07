"""Smooth Sesame-style walk for Orange: Rest -> Stand -> walk (diagonal pairs) -> Stand -> Rest.

Same diagonal pairs as Sesame's runWalkPose: A = (R1, L2), B = (R2, L1).
Same Stand / Rest servo angles as Sesame. Same angle mapping as gait.py (hip 90 = straight out, knee Stand value = straight down).
Walk direction: +X (display end). Hips swing +-HIP_AMP deg around the 45 deg Stand splay, so no hip ever turns toward the
body middle (shell clearance), knees lift KNEE_LIFT deg outward in a smooth arc.
"""
import os
try:  # repo root, found from this file's location
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
except NameError:  # exec'd inside Fusion: set ORANGE_ROOT to the repo folder
    ROOT = os.environ.get('ORANGE_ROOT', os.getcwd())
import numpy as np, sys
SP = os.path.join(ROOT, 'scripts/walk')
src = open(SP + '/gait.py').read()
head, tail = src.split('# --- Sesame keyframes')[0], 'def inter_vol' + src.split('def inter_vol', 1)[1]
geometry = '# --- geometry ---' + src.split('# --- geometry ---', 1)[1].split('\nframes = []', 1)[0]
exec(head)
exec(geometry)          # loads the parts, knee axes, leg_tf() and angles()

HIP_AMP = 20.0       # deg each way around the stand splay
KNEE_LIFT = 35.0     # deg peak knee lift during swing
CYCLES = 3
PER_CYCLE = 36       # frames per full step cycle (both pairs step once)
STAND = dict(R1=135, R2=45, L1=45, L2=135, R4=0, R3=180, L3=0, L4=180)
REST = {k: 90 for k in STAND}
SIDE = dict(L1=-1, L2=-1, R1=1, R2=1)            # -Y side (L) / +Y side (R)
PAIR_A = ('R1', 'L2')                              # Sesame's first diagonal pair
KNEE_OF = {'L1': 'L3', 'L2': 'L4', 'R1': 'R3', 'R2': 'R4'}
KNEE_STAND = {'R4': 0, 'R3': 180, 'L3': 0, 'L4': 180}

def ease(t):                     # smooth 0..1
    t = min(max(t, 0.0), 1.0); return 0.5 - 0.5 * np.cos(np.pi * t)

def servo_state(phi, lift):
    """phi[leg] = foot fore/aft offset in deg (+ = toward +X / display), lift[leg] = knee lift deg."""
    s = {}
    for leg in ('L1', 'L2', 'R1', 'R2'):
        d_stand = STAND[leg] - 90                  # Sesame stand splay (R1 +45, R2 -45, L1 -45, L2 +45)
        # CCW (+d) moves the foot toward -X on the +Y side and toward +X on the -Y side
        d = d_stand + (-1 if SIDE[leg] > 0 else 1) * phi[leg]
        s[leg] = 90 + d
        kn = KNEE_OF[leg]; ks = KNEE_STAND[kn]
        s[kn] = ks + (lift[leg] if ks == 0 else -lift[leg])
    return s

frames = []
def blend(a, b, n, label):
    for i in range(1, n + 1):
        t = ease(i / n); frames.append((label, {k: a[k] + (b[k] - a[k]) * t for k in a}))

frames.append(('rest (zero, all 90)', REST))
blend(REST, STAND, 14, 'rest -> stand')
for _ in range(4): frames.append(('stand', STAND))
total = CYCLES * PER_CYCLE
for i in range(total + 1):
    t = i / PER_CYCLE                               # cycles elapsed
    amp = HIP_AMP * min(ease(t / 0.5), ease((CYCLES - t) / 0.5))   # ramp in over the first half step, out over the last
    ph = 2 * np.pi * t
    phi, lift = {}, {}
    for leg in ('L1', 'L2', 'R1', 'R2'):
        sgn = 1 if leg in PAIR_A else -1
        phi[leg] = -sgn * amp * np.cos(ph) if t > 0 else 0.0
        # swing (lifted) while this leg's foot moves forward
        sw = np.sin(ph) * sgn
        lift[leg] = KNEE_LIFT * max(0.0, sw) ** 1.2 * (amp / HIP_AMP)
    # start: ease phi from 0 at t=0 using amp ramp (cos term ok since amp(0)=0)
    frames.append(('walk  step cycle %.2f' % t, servo_state(phi, lift)))
for _ in range(4): frames.append(('stand', STAND))
blend(STAND, REST, 14, 'stand -> rest')
print('frames', len(frames))
exec(tail)
