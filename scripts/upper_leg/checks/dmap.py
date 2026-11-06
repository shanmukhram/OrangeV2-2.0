import trimesh, numpy as np, sys
def depthmap(mesh, axis, start, sign, u_ax, v_ax, ur, vr, step=0.1):
    us=np.arange(ur[0],ur[1]+1e-9,step); vs=np.arange(vr[0],vr[1]+1e-9,step)
    U,V=np.meshgrid(us,vs,indexing='ij')
    O=np.zeros((U.size,3)); O[:,axis]=start; O[:,u_ax]=U.ravel(); O[:,v_ax]=V.ravel()
    D=np.zeros_like(O); D[:,axis]=sign
    loc,ir,it=mesh.ray.intersects_location(O,D,multiple_hits=True)
    out=np.full(U.size,np.nan)
    if len(ir):
        d=np.abs(loc[:,axis]-start)
        order=np.lexsort((d,ir))
        ir2=ir[order]; d2=d[order]; loc2=loc[order]
        first=np.r_[True,ir2[1:]!=ir2[:-1]]
        out[ir2[first]]=loc2[first][:,axis]
    return us,vs,out.reshape(U.shape)
MAPS={
 'hip_inner':(1,30.0,+1,0,2,(-12.4,7.8),(-41.9,-16.7)),     # rays +y onto inner face (z above arm)
 'hip_outer':(1,45.0,-1,0,2,(-12.4,7.8),(-47.1,-16.7)),
 'knee_inner':(0,-7.0,-1,1,2,(9.0,24.0),(-66.1,-41.0)),
 'knee_outer':(0,-20.0,+1,1,2,(9.0,24.0),(-66.1,-41.0)),
}
if __name__=='__main__':
    f=sys.argv[1]; out=sys.argv[2]
    m=trimesh.load(f)
    try:
        from trimesh.ray.ray_pyembree import RayMeshIntersector
    except Exception: pass
    res={}
    for k,a in MAPS.items():
        us,vs,d=depthmap(m,*a); res[k]=d; res[k+'_u']=us; res[k+'_v']=vs
        print(k, d.shape, np.nanmin(d), np.nanmax(d), np.isnan(d).sum())
    np.savez(out,**res)
