"""Skirt face pattern variants for the skirt cover (Fusion, exec into the concept design).
Skirt faces: y = 23.92 (R) and y = -28.68 (L); usable x -7..58.4, z -6.6..6.07. Coordinates in mm."""
import adsk.core, adsk.fusion, math

P = adsk.core.Point3D.create
VI = adsk.core.ValueInput
FO = adsk.fusion.FeatureOperations
FACES = (23.92, -28.68)
SP = r'C:/Users/admin/Desktop/HEXA-Orange/scripts/bottom_cover'   # side_shot() saves its PNGs here


def chamf_rect(x0, x1, z0, z1, c, corners='abcd'):
    """rect with 45 deg chamfers on chosen corners: a=bottom-left b=bottom-right c=top-right d=top-left"""
    pts = []
    pts += [(x0, z0 + c), (x0 + c, z0)] if 'a' in corners else [(x0, z0)]
    pts += [(x1 - c, z0), (x1, z0 + c)] if 'b' in corners else [(x1, z0)]
    pts += [(x1, z1 - c), (x1 - c, z1)] if 'c' in corners else [(x1, z1)]
    pts += [(x0 + c, z1), (x0, z1 - c)] if 'd' in corners else [(x0, z1)]
    return pts


def slot(xc, z0, z1, w, lean):
    """slanted slot: parallelogram, bottom centre xc, leaning +x by `lean` over its height"""
    return [(xc - w / 2, z0), (xc + w / 2, z0), (xc + w / 2 + lean, z1), (xc - w / 2 + lean, z1)]


VARIANTS = {
    # A: echoes the top shell side: long panel with slanted ends + 4 slanted vent slots at the front
    'A': [('poly', [(-4.0, -3.8), (30.0, -3.8), (35.0, 3.0), (1.0, 3.0)], 0.6)] +
         [('poly', slot(39.0 + 4.0 * i, -3.8, 3.0, 1.6, 2.4), 0.8) for i in range(4)],
    # B: three armour plates, like the spine on the bottom (outer corners chamfered)
    'B': [('poly', chamf_rect(-4.6, 13.4, -4.6, 3.8, 2.6, 'ad'), 0.6),
          ('poly', chamf_rect(15.4, 33.4, -4.6, 3.8, 0, ''), 0.6),
          ('poly', chamf_rect(35.4, 55.4, -4.6, 3.8, 2.6, 'bc'), 0.6)],
    # C: mech panel lines with bolt heads: raised plate outline groove with a kink + 4 bolts
    'C': [('poly', [(-4.6, 2.6), (24.0, 2.6), (28.0, -1.0), (55.4, -1.0), (55.4, 0.0), (28.4, 0.0), (24.4, 3.6), (-4.6, 3.6)], 0.6),
          ('poly', [(-4.6, -4.6), (55.4, -4.6), (55.4, -3.6), (-4.6, -3.6)], 0.6)] +
         [('circle', (x, z, 0.9), 0.5) for x, z in ((-2.6, 0.2), (14.0, 0.2), (38.0, -2.2), (53.4, 1.8))],
}


def build_variant(key):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    body = root.bRepBodies.itemByName('BottomCover')
    ext = root.features.extrudeFeatures
    feats = []
    base = root.xZConstructionPlane
    comp = round(base.geometry.normal.y)
    for yi, yf in enumerate(FACES):
        pi = root.constructionPlanes.createInput()
        pi.setByOffset(base, VI.createByReal(yf / 10 * comp))
        pl = root.constructionPlanes.add(pi); pl.isLightBulbOn = False
        pl.name = 'Var%s_plane%d' % (key, yi)
        for si, (kind, geo, depth) in enumerate(VARIANTS[key]):
            sk = root.sketches.add(pl); sk.name = 'Var%s_%d_%d' % (key, yi, si); sk.isVisible = False
            if kind == 'poly':
                sp = [sk.modelToSketchSpace(P(x / 10, yf / 10, z / 10)) for x, z in geo]
                ln = sk.sketchCurves.sketchLines
                first = ln.addByTwoPoints(sp[0], sp[1]); prev = first
                for q in sp[2:]:
                    prev = ln.addByTwoPoints(prev.endSketchPoint, q)
                ln.addByTwoPoints(prev.endSketchPoint, first.startSketchPoint)
            else:
                x, z, r = geo
                sk.sketchCurves.sketchCircles.addByCenterRadius(sk.modelToSketchSpace(P(x / 10, yf / 10, z / 10)), r / 10)
            prof = sk.profiles.item(0)
            done = False
            for flip in (False, True):
                ei = ext.createInput(prof, FO.CutFeatureOperation)
                ei.setDistanceExtent(flip, VI.createByReal(depth / 10)); ei.participantBodies = [body]
                v0 = body.volume
                try:
                    f = ext.add(ei)
                except Exception:
                    continue
                if body.volume < v0 - 1e-7:
                    f.name = 'Var%s_%d_%d' % (key, yi, si); feats.append(f); done = True; break
                f.deleteMe()
            assert done, (key, yi, si)
    return feats


def set_suppressed(prefix, sup):
    design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    tl = design.timeline
    for i in range(tl.count):
        it = tl.item(i)
        if it.entity is not None and hasattr(it.entity, 'name') and it.entity.name.startswith(prefix) \
                and isinstance(it.entity, adsk.fusion.ExtrudeFeature):
            it.isSuppressed = sup


def side_shot(fn):
    app = adsk.core.Application.get(); vp = app.activeViewport; cam = vp.camera
    cam.target = P(2.6, -0.2, 0.3); cam.eye = P(2.6, 39.8, 0.3)
    cam.upVector = adsk.core.Vector3D.create(0, 0, 1); cam.viewExtents = 12; cam.isFitView = False
    vp.camera = cam; vp.refresh(); vp.saveAsImageFile(SP + '/' + fn, 1400, 700)
