import numpy as np, json, sys
from shapely.geometry import Polygon, Point
from shapely import vectorized
a=np.load('orig_maps.npz'); b=np.load(sys.argv[1]); pk=json.load(open('pk.json'))
HIP=Polygon(pk['hip']); KNEE=Polygon(pk['knee'])
def grid(k):
    U,V=np.meshgrid(a[k+'_u'],a[k+'_v'],indexing='ij'); return U,V
def report(k,mask,label):
    A=a[k][mask]; B=b[k][mask]
    nanmis=(np.isnan(A)!=np.isnan(B)).sum()
    ok=~np.isnan(A)&~np.isnan(B); d=np.abs(A[ok]-B[ok])
    print('%-28s px=%5d nan-mismatch=%3d  maxdiff=%.3f  >0.05:%d  >0.1:%d'%(label,mask.sum(),nanmis,d.max() if len(d) else 0,(d>0.05).sum(),(d>0.1).sum()))
for k,poly in [('hip_inner',HIP),('knee_inner',KNEE)]:
    U,V=grid(k)
    inside=vectorized.contains(poly,U,V)
    dist=np.array([poly.exterior.distance(Point(u,v)) for u,v in zip(U.ravel(),V.ravel())]).reshape(U.shape)
    report(k,inside&(dist>0.15),k+' pocket (core)')
    report(k,inside&(dist<=0.15),k+' pocket wall band')
    report(k,~inside&(dist<1.3),k+' mouth ring 0-1.3')
for k,cs in [('hip_outer',[(1.52,-23.02),(1.52,-34.45)]),('knee_outer',[(15.23,-59.85),(15.23,-48.42)])]:
    U,V=grid(k)
    for c in cs:
        r=np.hypot(U-c[0],V-c[1]); report(k,r<4.0,'%s hole %s'%(k,c))
