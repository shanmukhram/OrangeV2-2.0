"""Orange bottom cover v2 (Fusion script, run with exec + build()).

Base frame (mm): +X front (display), +Y = R side, +Z up. Battery tube bottom at z = -4.
Rear (x = -35): a tongue slides into the base slot 'CoverTongueSlot' (y -9.38..4.62, z -2.7..-1.0, 1.5 deep).
Front (x = 88.6): a springy arm with a square-bottomed hook snaps into 'CoverLatchPocket'
(y -8.38..3.62, z 4.2..5.8, 1.4 deep). Release: pull the front tab forward (+X).
"""
import adsk.core, adsk.fusion, math

P = adsk.core.Point3D.create
VI = adsk.core.ValueInput
FO = adsk.fusion.FeatureOperations

T = 3.6                      # plate thickness: 1.6 solid + 2.0 mm deep inlay slots
Z0 = -4.0                    # battery tube bottom (plate top)
ZB = Z0 - T                  # plate bottom (outer face)
TUBE_Y = (-26.26, 21.5)      # battery tube side faces
GAP = 0.2
WALL = 2.22                  # outer face flush with the body sides (y -28.68 / 23.92)
WALL_TOP = -1.0
X_REAR, X_FRONT = -35.0, 88.6
SIDE_END = 82.6              # side walls stop before the wider front block (x 83..88.6)
YC = -2.38
# rear tab + tongue
TAB_Y = (-9.18, 4.42)
TAB_X = (-37.2, -35.2)
TAB_TOP = -0.6
TONGUE = [(-35.2, -2.5), (-33.8, -2.5), (-33.8, -1.6), (-35.2, -1.2)]       # (x, z)
# front spring arm + hook + release tab
ARM_Y = (-8.18, 3.42)
ARM_X = (89.0, 90.0)          # 1.0 thick, 0.4 relief gap to the plate end / base face
ARM_Z = (-4.6, 6.0)           # free length ~9.6 mm, 0.27 below the main-block overhang (z 6.27)
HOOK = [(89.0, 4.4), (87.5, 4.4), (87.5, 4.8), (89.0, 5.6)]               # square bottom, ramp on top
PULL = (90.0, 93.6, 5.0, 6.0)  # x0, x1, z0, z1
SCREWS = [(-33.0, 10.0), (-33.0, -14.0), (85.0, 10.0), (85.0, -14.0)]
SCREW_D, CSK_D = 2.4, 4.4
# side skirts: fill the strip between the rear and front hip servos up to the body underside
SKIRT_X = (-7.0, 58.4)        # servo bodies end at x -7.6 / start at 59.0 -> 0.6 clearance
SKIRT_TOP = 6.07              # body underside 6.27 -> 0.2 gap
PANEL = dict(x=(-3.6, 55.0), z=(-5.4, 3.6), ch=2.0, depth=0.6)   # chamfered recess on the skirt face


def build(name='Orange_BottomCover_v2'):
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = design.rootComponent
    ext = root.features.extrudeFeatures

    def plane(axis, c):
        base = [root.yZConstructionPlane, root.xZConstructionPlane, root.xYConstructionPlane][axis]
        n = base.geometry.normal; comp = round([n.x, n.y, n.z][axis])
        pi = root.constructionPlanes.createInput()
        pi.setByOffset(base, VI.createByReal(c / 10 * comp))
        pl = root.constructionPlanes.add(pi); pl.isLightBulbOn = False
        return pl

    def to3(axis, c, u, v):
        return [(c, u, v), (u, c, v), (u, v, c)][axis]

    def prism(axis, c0, c1, pts, op, nm, body=None):
        pl = plane(axis, c0)
        sk = root.sketches.add(pl); sk.name = nm
        sp = [sk.modelToSketchSpace(P(*[t / 10 for t in to3(axis, c0, u, v)])) for u, v in pts]
        ln = sk.sketchCurves.sketchLines
        first = ln.addByTwoPoints(sp[0], sp[1]); prev = first
        for q in sp[2:]:
            prev = ln.addByTwoPoints(prev.endSketchPoint, q)
        ln.addByTwoPoints(prev.endSketchPoint, first.startSketchPoint)
        prof = max([sk.profiles.item(i) for i in range(sk.profiles.count)], key=lambda p: p.areaProperties().area)
        for flip in (False, True):
            ei = ext.createInput(prof, op)
            ei.setDistanceExtent(flip, VI.createByReal(abs(c1 - c0) / 10))
            if body is not None: ei.participantBodies = [body]
            v0 = body.volume if body is not None else 0
            try:
                f = ext.add(ei)
            except Exception:
                continue
            if op == FO.CutFeatureOperation:
                if body.volume < v0 - 1e-6:
                    f.name = nm; return f
                f.deleteMe(); continue
            bb = f.bodies.item(0).boundingBox if f.bodies.count else None
            lo = [bb.minPoint.x, bb.minPoint.y, bb.minPoint.z][axis] * 10 if bb else None
            hi = [bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z][axis] * 10 if bb else None
            want_lo, want_hi = min(c0, c1), max(c0, c1)
            if op != FO.NewBodyFeatureOperation or (lo is not None and lo <= want_lo + 0.01 and hi >= want_hi - 0.01):
                f.name = nm
                return f
            f.deleteMe()
        raise RuntimeError('direction failed for ' + nm)

    def rect(x0, x1, y0, y1):
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    yo = (TUBE_Y[0] - GAP - WALL, TUBE_Y[1] + GAP + WALL)
    # plate
    f = prism(2, ZB, Z0, rect(X_REAR, X_FRONT, yo[0], yo[1]), FO.NewBodyFeatureOperation, 'Plate')
    body = f.bodies.item(0); body.name = 'BottomCover'
    J = FO.JoinFeatureOperation
    # side walls hugging the battery tube
    prism(2, Z0, WALL_TOP, rect(X_REAR, SIDE_END, yo[0], TUBE_Y[0] - GAP), J, 'WallL', body)
    prism(2, Z0, WALL_TOP, rect(X_REAR, SIDE_END, TUBE_Y[1] + GAP, yo[1]), J, 'WallR', body)
    prism(2, Z0, SKIRT_TOP, rect(SKIRT_X[0], SKIRT_X[1], yo[0], TUBE_Y[0] - GAP), J, 'SkirtL', body)
    prism(2, Z0, SKIRT_TOP, rect(SKIRT_X[0], SKIRT_X[1], TUBE_Y[1] + GAP, yo[1]), J, 'SkirtR', body)
    # rear tab + tongue
    prism(2, ZB, Z0, rect(TAB_X[0], X_REAR, TAB_Y[0], TAB_Y[1]), J, 'TabRoot', body)
    prism(2, Z0, TAB_TOP, rect(TAB_X[0], TAB_X[1], TAB_Y[0], TAB_Y[1]), J, 'RearTab', body)
    prism(1, TAB_Y[0], TAB_Y[1], TONGUE, J, 'Tongue', body)
    # front spring arm: joined to the plate only through a root block under the relief gap
    prism(2, ZB, ARM_Z[0], rect(X_FRONT, ARM_X[1], ARM_Y[0], ARM_Y[1]), J, 'ArmRoot', body)
    prism(2, ARM_Z[0], ARM_Z[1], rect(ARM_X[0], ARM_X[1], ARM_Y[0], ARM_Y[1]), J, 'LatchArm', body)
    prism(1, ARM_Y[0], ARM_Y[1], HOOK, J, 'Hook', body)
    prism(2, PULL[2], PULL[3], rect(PULL[0], PULL[1], ARM_Y[0], ARM_Y[1]), J, 'PullTab', body)
    # recessed tactical panel on each skirt face
    (px0, px1), (pz0, pz1), pc, pd = PANEL['x'], PANEL['z'], PANEL['ch'], PANEL['depth']
    ppoly = [(px0 + pc, pz0), (px1 - pc, pz0), (px1, pz0 + pc), (px1, pz1 - pc), (px1 - pc, pz1), (px0 + pc, pz1), (px0, pz1 - pc), (px0, pz0 + pc)]
    FC = FO.CutFeatureOperation
    for nm, yface, yin in (('PanelL', yo[0], yo[0] + pd), ('PanelR', yo[1], yo[1] - pd)):
        v0 = body.volume
        prism(1, yface, yin, ppoly, FC, nm, body)
        assert body.volume < v0, nm
    # optional screw holes with countersinks on the outer face
    for i, (sx, sy) in enumerate(SCREWS):
        pl = plane(2, ZB)
        sk = root.sketches.add(pl); sk.name = 'screw_%d' % i
        sk.sketchCurves.sketchCircles.addByCenterRadius(sk.modelToSketchSpace(P(sx / 10, sy / 10, ZB / 10)), SCREW_D / 20)
        for flip in (False, True):
            ei = ext.createInput(sk.profiles.item(0), FO.CutFeatureOperation)
            ei.setDistanceExtent(flip, VI.createByReal(T / 10 + 0.01)); ei.participantBodies = [body]
            v0 = body.volume
            fh = ext.add(ei)
            if body.volume < v0 - 1e-6: fh.name = 'ScrewHole%d' % i; break
            fh.deleteMe()
    cham = root.features.chamferFeatures
    col = adsk.core.ObjectCollection.create()
    for e in body.edges:
        if e.geometry.curveType == adsk.core.Curve3DTypes.Circle3DCurveType:
            bb = e.boundingBox
            if abs(bb.minPoint.z * 10 - ZB) < 1e-3 and abs(bb.maxPoint.z * 10 - ZB) < 1e-3:
                col.add(e)
    if col.count:
        ci = cham.createInput2()
        ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(col, VI.createByReal((CSK_D - SCREW_D) / 20), False)
        cham.add(ci).name = 'Countersinks'
    print('screw holes', col.count)

    def chamfer(edges, d, nm):
        if edges.count == 0: return
        try:
            ci = cham.createInput2()
            ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges, VI.createByReal(d / 10), False)
            cham.add(ci).name = nm
            print(nm, edges.count, 'edges')
        except Exception as e:
            print(nm, 'failed', str(e)[:80])

    def on(v, val): return abs(v * 10 - val) < 1e-3
    # rocking bevel: plate top edge along the rear end, so the cover can pivot on its tongue
    col = adsk.core.ObjectCollection.create()
    for e in body.edges:
        bb = e.boundingBox
        if on(bb.minPoint.x, X_REAR) and on(bb.maxPoint.x, X_REAR) and on(bb.minPoint.z, Z0) and on(bb.maxPoint.z, Z0):
            col.add(e)
    chamfer(col, 0.8, 'RockBevel')
    # outer face: soft chamfer around the outside of the plate bottom
    col = adsk.core.ObjectCollection.create()
    for f in body.faces:
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType: continue
        bb = f.boundingBox
        if on(bb.minPoint.z, ZB) and on(bb.maxPoint.z, ZB):
            for lp in f.loops:
                if lp.isOuter:
                    for e in lp.edges:
                        eb = e.boundingBox
                        if eb.minPoint.x * 10 > X_FRONT - 0.01 or eb.maxPoint.x * 10 < X_REAR + 0.01:
                            continue        # leave edges lying on the end faces square (arm root, tab root)
                        col.add(e)
    chamfer(col, 1.0, 'OuterChamfer')

    # ---- shell-style inlay pockets on the outside face + matching accent-colour inlay pieces ----
    def inset(poly, d):
        """Shrink a convex polygon by d (mm) on every side."""
        n = len(poly)
        area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
        s = 1.0 if area > 0 else -1.0          # CCW: inward normal is to the left
        lines = []
        for i in range(n):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
            dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy)
            nx, ny = -dy / L * s, dx / L * s
            lines.append(((x0 + nx * d, y0 + ny * d), (dx, dy)))
        out = []
        for i in range(n):
            (p, r), (q, t) = lines[i - 1], lines[i]
            den = r[0] * t[1] - r[1] * t[0]
            u = ((q[0] - p[0]) * t[1] - (q[1] - p[1]) * t[0]) / den
            out.append((p[0] + r[0] * u, p[1] + r[1] * u))
        return out

    yl, yh, ch = YC - 10.0, YC + 10.0, 6.0          # central spine, 20 wide, 6 mm chamfered ends
    segs = [(-22.0, 0.8), (2.4, 25.2), (26.8, 49.6), (51.2, 74.0)]   # 4 segments, 1.6 mm ribs (like the top shell)
    shapes = {}
    for k, (a, b2) in enumerate(segs):
        if k == 0:
            shapes['Spine%d' % (k + 1)] = [(a + ch, yl), (b2, yl), (b2, yh), (a + ch, yh), (a, yh - ch), (a, yl + ch)]
        elif k == len(segs) - 1:
            shapes['Spine%d' % (k + 1)] = [(a, yl), (b2 - ch, yl), (b2, yl + ch), (b2, yh - ch), (b2 - ch, yh), (a, yh)]
        else:
            shapes['Spine%d' % (k + 1)] = rect(a, b2, yl, yh)
    sy0, sy1 = YC + 14.38, YC + 16.98                 # slanted side stripes, 2.6 wide, mirrored about the centreline
    shapes['StripeR'] = [(-18.0, sy0), (70.0, sy0), (72.6, sy1), (-15.4, sy1)]
    my = lambda y: 2 * YC - y
    shapes['StripeL'] = [(-15.4, my(sy1)), (72.6, my(sy1)), (70.0, my(sy0)), (-18.0, my(sy0))]
    DEPTH, CLR = 2.0, 0.15
    inlays = []
    for nm, poly in shapes.items():
        pl = plane(2, ZB)
        sk = root.sketches.add(pl); sk.name = 'pocket_' + nm
        sp = [sk.modelToSketchSpace(P(u / 10, v / 10, ZB / 10)) for u, v in poly]
        ln = sk.sketchCurves.sketchLines
        first = ln.addByTwoPoints(sp[0], sp[1]); prev = first
        for q in sp[2:]: prev = ln.addByTwoPoints(prev.endSketchPoint, q)
        ln.addByTwoPoints(prev.endSketchPoint, first.startSketchPoint)
        for flip in (False, True):
            ei = ext.createInput(sk.profiles.item(0), FO.CutFeatureOperation)
            ei.setDistanceExtent(flip, VI.createByReal(DEPTH / 10)); ei.participantBodies = [body]
            v0 = body.volume; fc = ext.add(ei)
            if body.volume < v0 - 1e-6: fc.name = 'Pocket' + nm; break
            fc.deleteMe()
        f = prism(2, ZB, ZB + DEPTH, inset(poly, CLR), FO.NewBodyFeatureOperation, 'Inlay' + nm)
        ib = f.bodies.item(0); ib.name = 'Inlay_' + nm
        inlays.append(ib)
    print('inlay pockets + pieces', len(inlays))
    return design, body
