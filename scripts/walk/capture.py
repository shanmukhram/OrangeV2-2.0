import adsk.core, adsk.fusion, json, os

SP = r'C:/Users/admin/Desktop/HEXA-Orange/scripts/walk'


def mat(T):
    m = adsk.core.Matrix3D.create(); a = []
    for r in range(4):
        for c in range(4):
            v = T[r][c]
            if c == 3 and r < 3: v = v / 10.0
            a.append(v)
    m.setWithArray(a); return m


def capture(start, end, outdir, keep_camera=False):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    assert root.occurrences.itemByName('Base_wide:1') is not None
    G = json.load(open(SP + '/gait_frames.json'))
    info = json.load(open(r'C:/Users/admin/Desktop/HEXA-Orange/scripts/assembly/asm/info.json'))
    occ = {}; T0 = {}
    for leg, nm in G['names'].items():
        for part, on in nm.items():
            o = root.occurrences.itemByName(on); occ[(leg, part)] = o
            m = adsk.core.Matrix3D.create(); m.setWithArray(info[on.replace(':', '_')]['T']); T0[(leg, part)] = m
    os.makedirs(outdir, exist_ok=True)
    vp = app.activeViewport

    def view(kind):
        cam = vp.camera
        if kind == 'iso':
            cam.target = adsk.core.Point3D.create(2.0, -0.2, -0.8)
            cam.eye = adsk.core.Point3D.create(2.0 + 22, -0.2 - 26, -0.8 + 19)
            cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
            cam.viewExtents = 24.0
        else:
            cam.target = adsk.core.Point3D.create(2.6, -0.2, 0)
            cam.eye = adsk.core.Point3D.create(2.6, -0.2, 60)
            cam.upVector = adsk.core.Vector3D.create(1, 0, 0)     # display end (front, +X) at the top
            cam.viewExtents = 20.0
        cam.isFitView = False
        vp.camera = cam

    n = 0
    if not keep_camera:
        view('iso')                 # camera is set once and never moved during the recording
    try:
        for fi in range(start, min(end, len(G['frames']))):
            f = G['frames'][fi]
            for leg, parts in f['tfs'].items():
                for part, D in parts.items():
                    T = T0[(leg, part)].copy(); T.transformBy(mat(D)); occ[(leg, part)].transform2 = T
            vp.refresh()
            if keep_camera:
                vp.saveAsImageFile(outdir + '/iso_%03d.png' % fi, 0, 0)   # 0,0 = the viewport's own size and framing
            else:
                vp.saveAsImageFile(outdir + '/iso_%03d.png' % fi, 960, 640)
            n += 1
    finally:
        for k, o in occ.items(): o.transform2 = T0[k]
        vp.refresh()
    return n, len(G['frames'])
