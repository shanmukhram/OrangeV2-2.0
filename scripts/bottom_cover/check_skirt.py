import os
try:  # repo root, found from this file's location
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
except NameError:  # exec'd inside Fusion: set ORANGE_ROOT to the repo folder
    ROOT = os.environ.get('ORANGE_ROOT', os.getcwd())
import trimesh, numpy as np, json, manifold3d as m3
# Gap checks for the skirt cover (base frame, mm). Needs: pip install numpy trimesh manifold3d
R = os.path.join(ROOT, '')
ASM = R + 'scripts/assembly/asm/'
info=json.load(open(ASM + 'info.json'))
def L(p,key=None):
    m=trimesh.load(p)
    if key:
        T=np.array(info[key]['T']).reshape(4,4).copy(); T[:3,3]*=10; m.apply_transform(T)
    return m
def M(t): return m3.Manifold(m3.Mesh(np.asarray(t.vertices,np.float32),np.asarray(t.faces,np.uint32)))
cov=M(trimesh.load(R + 'output/v2/Orange_BottomCover_Skirt_v2/Orange_BottomCover_Skirt_v2.stl'))
print('has min_gap', hasattr(cov,'min_gap'))
base=M(trimesh.load(R + 'output/v2/Orange_Base_BatteryHolder_v2.stl'))
print('base gap', round(cov.min_gap(base,5),3))
for i in (2,4,6,8): print('servo',i, round(cov.min_gap(M(L(ASM + 'MG90S_%d.stl'%i,'MG90S_%d'%i)),10),2))
G=json.load(open(R + 'scripts/walk/gait_frames.json')); parts={}
for leg,nm in G['names'].items():
    for p,on in nm.items(): parts[(leg,p)]=L(ASM+on.replace(':','_')+'.stl',on.replace(':','_'))
worst=(99,None)
for fi,f in enumerate(G['frames'][::2]):
    for leg,pp in f['tfs'].items():
        for p,D in pp.items():
            m=parts[(leg,p)].copy(); m.apply_transform(np.array(D,float).reshape(4,4))
            g=cov.min_gap(M(m),30)
            if g<worst[0]: worst=(g,(fi*2,leg,p,f['label']))
print('walk worst gap',round(worst[0],2),worst[1])
