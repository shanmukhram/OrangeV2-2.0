import trimesh, numpy as np, sys
m=trimesh.load(sys.argv[1]); thr=float(sys.argv[2]) if len(sys.argv)>2 else 1.0
pts,fi=trimesh.sample.sample_surface_even(m,60000,seed=1)
n=m.face_normals[fi]
# distance to sharp edges
fa=m.face_adjacency_angles; sharp=m.face_adjacency_edges[fa>np.radians(30)]
segs=m.vertices[sharp]
def dseg(p,a,b):
    ab=b-a; t=np.clip(((p[:,None,:]-a)*ab).sum(-1)/np.maximum((ab*ab).sum(-1),1e-12),0,1)
    return np.linalg.norm(p[:,None,:]-(a+t[...,None]*ab),axis=-1).min(1)
dd=np.concatenate([dseg(pts[i:i+2000],segs[:,0],segs[:,1]) for i in range(0,len(pts),2000)])
keep=dd>0.15; pts=pts[keep]; n=n[keep]
O=pts-n*1e-3; loc,ir,_=m.ray.intersects_location(O,-n,multiple_hits=False)
t=np.full(len(O),np.inf); t[ir]=np.linalg.norm(loc-O[ir],axis=1)
bad=t<thr
print('samples',len(O),'thin<%.2f:'%thr,bad.sum())
if bad.sum():
    from scipy.cluster.hierarchy import fcluster, linkage
    P=pts[bad]; T=t[bad]
    if len(P)>1:
        cl=fcluster(linkage(P,'single'),1.0,'distance')
    else: cl=np.array([1])
    for c in np.unique(cl):
        k=cl==c; print('  cluster n=%d min=%.2f at %s'%(k.sum(),T[k].min(),P[k][T[k].argmin()].round(2)))
