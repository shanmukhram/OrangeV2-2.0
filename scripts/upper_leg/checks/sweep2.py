import os
try:  # repo root, found from this file's location
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
except NameError:  # exec'd inside Fusion: set ORANGE_ROOT to the repo folder
    ROOT = os.environ.get('ORANGE_ROOT', os.getcwd())
import trimesh, numpy as np, sys
S=os.path.join(ROOT, '')
LL=trimesh.load('LL2_aligned.stl')
L3=trimesh.load(S+"hexa-orange stl/L3-v117 (1).stl"); L3=max(L3.split(only_watertight=False),key=lambda p:p.volume)
def box(x0,x1,y0,y1,z0,z1):
    b=trimesh.creation.box(extents=[x1-x0,y1-y0,z1-z0]); b.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]); return b
servo=trimesh.boolean.union([box(-4.5,20,9.0,21.4,-76.45,-53.55), box(1.26,3.76,9.0,21.4,-81.25,-48.75)],engine='manifold')
servo.export('servo_env.stl')
def rot(m,ang):
    T=trimesh.transformations.rotation_matrix(np.radians(ang),[1,0,0],[0,15.23,-59.85]); c=m.copy(); c.apply_transform(T); return c
def iv(a,b):
    r=trimesh.boolean.intersection([a,b],engine='manifold'); return r.volume if len(r.faces) else 0.0
def free_range(L1,leg):
    hit=lambda ang: iv(L1,rot(leg,ang))>0.001
    lo=0
    while lo>-180 and not hit(lo-1): lo-=1
    hi=0
    while hi<180 and not hit(hi+1): hi+=1
    return lo,hi,hit(0)
for f in sys.argv[1:]:
    L1=trimesh.load(f)
    print(f)
    print('  servo env  :',free_range(L1,servo))
    print('  LL2 (new)  :',free_range(L1,LL))
    print('  L3 (orig)  :',free_range(L1,L3))
