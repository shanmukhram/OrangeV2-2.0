def run(context): pass
import adsk.core, adsk.fusion, math

HIP = {"c1": [1.523271480752892, -23.01679013358047], "r1": 4.004012298215972, "c2": [1.5228910847537453, -39.36823739786236], "r2": 2.6522164561613826, "Tp1": [5.513569810306109, -23.34789997250038], "Tm1": [-2.4670422501949534, -23.347714313527845], "Tp2": [4.16602354949411, -39.587561140691925], "Tm2": [-1.1202515817115994, -39.58743816210307]}
KNEE = {"c1": [15.402959168128286, -59.827551723634414], "r1": 3.765179679047764, "c2": [15.36866113403254, -43.4933269909387], "r2": 2.3954441330960785, "Tp1": [11.650386385085447, -59.51969538785366], "Tm1": [19.15420601478688, -59.50393912970737], "Tp2": [12.981237631462967, -43.29746577945755], "Tm2": [17.75524106290756, -43.28744149393777]}

app = adsk.core.Application.get()
P = adsk.core.Point3D.create
VI = adsk.core.ValueInput
FO = adsk.fusion.FeatureOperations

def cm(v): return v / 10.0

Y_IN, Y_OUT = 34.28, 39.358          # hip plate inner / outer face
Z_BOT, Z_TOP = -47.15, -42.07        # arm slab
X_OUT, X_IN = -12.447, -7.37         # knee tab outer / inner face
HIP_C = (1.52, -23.02); HIP_L = (1.52, -34.45)
KNEE_C = (15.23, -59.85); KNEE_L = (15.23, -48.42)
HIP_ARM, HIP_HUB = 36.691, 37.834
KNEE_ARM, KNEE_HUB = -9.691, -10.834
RAMP = [(6.34, 0.0), (6.5, .167), (6.7, .362), (6.9, .517), (7.1, .656), (7.3, .768), (7.5, .869),
        (7.7, .945), (7.9, 1.016), (8.2, 1.083), (8.5, 1.123), (8.8, 1.143)]
HOLE_R = 1.248
REUSE = globals().get('REUSE', False)
BEVEL_BR = 4.0
TOP_DIAG = 0
PANEL = [(17.86, -66.20), (39.358, -56.0), (39.358, -42.07), (25.0, -42.07), (19.5, -39.31), (11.6, -39.31), (8.88, -44.0), (8.88, -62.48), (12.60, -66.20)]
WIN = globals().get('WIN', {'panel': [], 'web': []})
BLADE = 1.4

def run(_context: str):
    design = adsk.fusion.Design.cast(app.activeProduct)
    if REUSE:
        tl = design.timeline
        tl.moveToBeginning()
        tl.deleteAllAfterMarker()
        for i in range(design.rootComponent.constructionPlanes.count - 1, -1, -1):
            design.rootComponent.constructionPlanes.item(i).deleteMe()
    else:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = design.rootComponent
    feats = root.features
    ext = feats.extrudeFeatures

    def plane_at(axis, c):
        base = [root.yZConstructionPlane, root.xZConstructionPlane, root.xYConstructionPlane][axis]
        n = base.geometry.normal
        comp = round([n.x, n.y, n.z][axis])
        pi = root.constructionPlanes.createInput()
        pi.setByOffset(base, VI.createByReal(cm(c) * comp))
        pl = root.constructionPlanes.add(pi)
        pl.isLightBulbOn = False
        return pl, comp

    def to3(axis, c, u, v):
        return [(c, u, v), (u, c, v), (u, v, c)][axis]

    def sk_poly(axis, c, pts, name):
        pl, comp = plane_at(axis, c)
        sk = root.sketches.add(pl)
        sk.name = name
        sp = [sk.modelToSketchSpace(P(*[cm(t) for t in to3(axis, c, u, v)])) for u, v in pts]
        lines = sk.sketchCurves.sketchLines
        first = lines.addByTwoPoints(sp[0], sp[1])
        prev = first
        for i in range(2, len(sp)):
            prev = lines.addByTwoPoints(prev.endSketchPoint, sp[i])
        lines.addByTwoPoints(prev.endSketchPoint, first.startSketchPoint)
        return sk, comp

    def bigprof(sk):
        return max([sk.profiles.item(i) for i in range(sk.profiles.count)],
                   key=lambda p: p.areaProperties().area)

    def sk_pocket(axis, c, info, name):
        pl, comp = plane_at(axis, c)
        sk = root.sketches.add(pl)
        sk.name = name
        T = lambda uv: sk.modelToSketchSpace(P(*[cm(t) for t in to3(axis, c, uv[0], uv[1])]))
        c1, c2 = info['c1'], info['c2']
        dx, dy = c2[0] - c1[0], c2[1] - c1[1]
        L = math.hypot(dx, dy); dx, dy = dx / L, dy / L
        m1 = (c1[0] - info['r1'] * dx, c1[1] - info['r1'] * dy)
        m2 = (c2[0] + info['r2'] * dx, c2[1] + info['r2'] * dy)
        arcs = sk.sketchCurves.sketchArcs
        a1 = arcs.addByThreePoints(T(info['Tp1']), T(m1), T(info['Tm1']))
        a2 = arcs.addByThreePoints(T(info['Tm2']), T(m2), T(info['Tp2']))
        def near(arc, uv):
            q = T(uv)
            sp, ep = arc.startSketchPoint, arc.endSketchPoint
            return sp if sp.geometry.distanceTo(q) < ep.geometry.distanceTo(q) else ep
        ln = sk.sketchCurves.sketchLines
        ln.addByTwoPoints(near(a1, info['Tm1']), near(a2, info['Tm2']))
        ln.addByTwoPoints(near(a2, info['Tp2']), near(a1, info['Tp1']))
        return sk, comp

    def prism(axis, c0, c1, pts, op, name, body=None):
        if isinstance(pts, dict):
            sk, comp = sk_pocket(axis, c0, pts, name)
        else:
            sk, comp = sk_poly(axis, c0, pts, name)
        ei = ext.createInput(bigprof(sk), op)
        ei.setDistanceExtent(False, VI.createByReal(cm(c1 - c0) * comp))
        if body is not None:
            ei.participantBodies = [body]
        f = ext.add(ei)
        f.name = name
        return f

    def revolve(axis, c, pts, ax_a, ax_b, op, name, body=None):
        # pts in plane coords; axis line from ax_a to ax_b (plane coords)
        sk, comp = sk_poly(axis, c, pts, name)
        a = sk.modelToSketchSpace(P(*[cm(t) for t in to3(axis, c, *ax_a)]))
        b = sk.modelToSketchSpace(P(*[cm(t) for t in to3(axis, c, *ax_b)]))
        ln = sk.sketchCurves.sketchLines.addByTwoPoints(a, b)
        ln.isConstruction = True
        ri = feats.revolveFeatures.createInput(bigprof(sk), ln, op)
        ri.setAngleExtent(False, VI.createByReal(2 * math.pi))
        if body is not None:
            ri.participantBodies = [body]
        f = feats.revolveFeatures.add(ri)
        f.name = name
        return f

    def circle_cut(axis, c0, c1, center, r, name, body):
        pl, comp = plane_at(axis, c0)
        sk = root.sketches.add(pl)
        sk.name = name
        cp = sk.modelToSketchSpace(P(*[cm(t) for t in to3(axis, c0, *center)]))
        sk.sketchCurves.sketchCircles.addByCenterRadius(cp, cm(r))
        ei = ext.createInput(sk.profiles.item(0), FO.CutFeatureOperation)
        ei.setDistanceExtent(False, VI.createByReal(cm(c1 - c0) * comp))
        ei.participantBodies = [body]
        f = ext.add(ei)
        f.name = name
        return f

    # ---------------- outer solid (concept) ----------------
    J = FO.JoinFeatureOperation
    plate = prism(1, Y_IN, Y_OUT, [(X_OUT, Z_BOT), (X_OUT, -26.0), (-3.5, -16.67), (4.16, -16.67),
                                   (7.87, -20.38), (7.87, Z_BOT)], FO.NewBodyFeatureOperation, 'HipShield')
    body = plate.bodies.item(0)
    body.name = 'UpperLeg'
    prism(0, X_OUT, X_IN, PANEL, J, 'ThighPanel', body)
    prism(2, Z_BOT, Z_TOP, [(X_IN, 20.0), (X_IN, 36.0), (7.87, 36.0), (7.87, Y_IN)], J, 'InnerWeb', body)

    # plate / arm inner corner fillet R2
    fe = adsk.core.ObjectCollection.create()
    for e in body.edges:
        bb = e.boundingBox
        if abs(bb.minPoint.y - cm(Y_IN)) < 1e-4 and abs(bb.maxPoint.y - cm(Y_IN)) < 1e-4 and \
           abs(bb.minPoint.z - cm(Z_TOP)) < 1e-4 and abs(bb.maxPoint.z - cm(Z_TOP)) < 1e-4:
            fe.add(e)
    fi = feats.filletFeatures.createInput()
    fi.addConstantRadiusEdgeSet(fe, VI.createByReal(cm(2.0)), True)
    feats.filletFeatures.add(fi).name = 'InnerCornerR2'
    print('inner fillet edges', fe.count)

    # ---------------- knee pocket arm part + horn slot ----------------
    prism(0, KNEE_ARM, 10.0, KNEE, FO.CutFeatureOperation, 'KneePocketSlot', body)
    # ---------------- hip pocket arm part ----------------
    prism(1, 30.0, HIP_ARM, HIP, FO.CutFeatureOperation, 'HipPocket', body)

    # hub deep parts: revolve ∩ outline prism, then cut
    def hubcut(name, axis_rev, c_rev, prof_pts, ax_a, ax_b, pr_axis, pr0, pr1, outline):
        rv = revolve(axis_rev, c_rev, prof_pts, ax_a, ax_b, FO.NewBodyFeatureOperation, name + 'Rev')
        pr = prism(pr_axis, pr0, pr1, outline, FO.NewBodyFeatureOperation, name + 'Prism')
        tools = adsk.core.ObjectCollection.create(); tools.add(pr.bodies.item(0))
        ci = feats.combineFeatures.createInput(rv.bodies.item(0), tools)
        ci.operation = FO.IntersectFeatureOperation
        feats.combineFeatures.add(ci).name = name + 'Intersect'
        tools = adsk.core.ObjectCollection.create(); tools.add(rv.bodies.item(0))
        ci = feats.combineFeatures.createInput(body, tools)
        ci.operation = FO.CutFeatureOperation
        feats.combineFeatures.add(ci).name = name + 'Cut'

    zc = HIP_C[1]
    hp = [(HIP_ARM, zc), (HIP_HUB, zc)] + [(HIP_HUB - d, zc - r) for r, d in RAMP] + [(HIP_ARM, zc - RAMP[-1][0])]
    hubcut('HipHub', 0, HIP_C[0], hp, (30.0, zc), (45.0, zc), 1, 36.0, 38.2, HIP)
    zc = KNEE_C[1]
    kp = [(KNEE_ARM, zc), (KNEE_HUB, zc)] + [(KNEE_HUB + d, zc + r) for r, d in RAMP] + [(KNEE_ARM, zc + RAMP[-1][0])]
    hubcut('KneeHub', 1, KNEE_C[0] + 0.18, kp, (-14.0, zc), (-5.0, zc), 0, -9.2, -11.2, KNEE)

    # ---------------- pocket mouth lead-in R1.25 ----------------
    def mouth(name, axis, c, outline):
        us = [outline['c1'][0] + outline['r1'] * k for k in (-1, 1)] + [outline['c2'][0] + outline['r2'] * k for k in (-1, 1)]
        vs = [outline['c1'][1] + outline['r1'] * k for k in (-1, 1)] + [outline['c2'][1] + outline['r2'] * k for k in (-1, 1)]
        lo = (min(us) - 0.3, min(vs) - 0.3); hi = (max(us) + 0.3, max(vs) + 0.3)
        col = adsk.core.ObjectCollection.create()
        for f in body.faces:
            if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType: continue
            bb = f.boundingBox
            if abs([bb.minPoint.x, bb.minPoint.y, bb.minPoint.z][axis] - cm(c)) > 1e-4: continue
            if abs([bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z][axis] - cm(c)) > 1e-4: continue
            for e in f.edges:
                q = e.pointOnEdge
                uv = [[q.y, q.z], [q.x, q.z], [q.x, q.y]][axis]
                if lo[0] <= uv[0] * 10 <= hi[0] and lo[1] <= uv[1] * 10 <= hi[1]:
                    col.add(e)
        fi = feats.filletFeatures.createInput()
        fi.addConstantRadiusEdgeSet(col, VI.createByReal(cm(1.25)), True)
        feats.filletFeatures.add(fi).name = name
        print(name, 'edges', col.count)
    mouth('HipMouthR125', 1, Y_IN, HIP)
    mouth('KneeMouthR125', 0, X_IN, KNEE)

    # ---------------- styling: bevels ----------------
    def tok_add(col, seen, e):
        if e.entityToken not in seen:
            seen.add(e.entityToken); col.add(e)
    # 45 deg bevel along the arm / plate bottom-right edge chain
    col = adsk.core.ObjectCollection.create(); seen = set()
    for e in body.edges:
        bb = e.boundingBox
        if abs(bb.minPoint.z - cm(Z_BOT)) < 1e-4 and abs(bb.maxPoint.z - cm(Z_BOT)) < 1e-4:
            q = e.pointOnEdge
            if q.x * 10 > -6.0 and q.y * 10 > 18.3 and q.y * 10 < Y_OUT - 0.1 and e.geometry.curveType == adsk.core.Curve3DTypes.Line3DCurveType:
                tok_add(col, seen, e)
    ci = feats.chamferFeatures.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(col, VI.createByReal(cm(BEVEL_BR)), False)
    feats.chamferFeatures.add(ci).name = 'BottomRightBevel'
    print('bottom-right bevel edges', col.count)
    # small chamfer on the arm's top diagonal edge (original was rounded there)
    col = adsk.core.ObjectCollection.create(); seen = set()
    for e in body.edges:
        bb = e.boundingBox
        if abs(bb.minPoint.z - cm(Z_TOP)) < 1e-4 and abs(bb.maxPoint.z - cm(Z_TOP)) < 1e-4:
            q = e.pointOnEdge
            if q.x * 10 > 0.5 and 18.3 < q.y * 10 < 34.0 and (bb.maxPoint.x - bb.minPoint.x) > 0.1 and e.geometry.curveType == adsk.core.Curve3DTypes.Line3DCurveType:
                tok_add(col, seen, e)
    if TOP_DIAG > 0:
        ci = feats.chamferFeatures.createInput2()
        ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(col, VI.createByReal(cm(TOP_DIAG)), False)
        feats.chamferFeatures.add(ci).name = 'ArmTopEdge'
    print('arm top edge chamfer edges', col.count)
    # blade bevels on the two big outer faces
    col = adsk.core.ObjectCollection.create(); seen = set()
    for f in body.faces:
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType: continue
        bb = f.boundingBox
        isback = abs(bb.minPoint.y - cm(Y_OUT)) < 1e-4 and abs(bb.maxPoint.y - cm(Y_OUT)) < 1e-4
        isside = abs(bb.minPoint.x - cm(X_OUT)) < 1e-4 and abs(bb.maxPoint.x - cm(X_OUT)) < 1e-4
        if not (isback or isside): continue
        for lp in f.loops:
            if lp.isOuter:
                for e in lp.edges: tok_add(col, seen, e)
    ci = feats.chamferFeatures.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(col, VI.createByReal(cm(BLADE)), False)
    feats.chamferFeatures.add(ci).name = 'BladeBevels'
    print('blade bevel edges', col.count)

    # ---------------- concept windows ----------------
    for k, w in enumerate(WIN['panel']):
        prism(0, X_OUT - 1.0, X_IN, w, FO.CutFeatureOperation, 'PanelWindow%d' % k, body)
    for k, w in enumerate(WIN['web']):
        prism(2, Z_BOT - 1.0, Z_TOP + 1.0, w, FO.CutFeatureOperation, 'WebWindow%d' % k, body)

    # ---------------- holes ----------------
    for nm, cxz in (('HipHoleC', HIP_C), ('HipHoleL', HIP_L)):
        circle_cut(1, 30.0, 41.0, cxz, HOLE_R, nm, body)
    for nm, cyz in (('KneeHoleC', KNEE_C), ('KneeHoleL', KNEE_L)):
        circle_cut(0, -14.0, -6.0, cyz, HOLE_R, nm, body)

    # ---------------- countersinks (measured profiles) ----------------
    def cs_hub(d0):   # list of (r, depth)
        return [(3.62 + 0.3 * 1.5875, -0.3), (3.62, 0.0), (1.25, 1.493)]
    def cs_low():
        return [(2.778 + 0.3 * 2.42, -0.3), (2.778, 0.0), (1.4746, 0.5386), (1.25, 0.761)]
    for nm, cxz, prof in (('HipCsC', HIP_C, cs_hub(0)), ('HipCsL', HIP_L, cs_low())):
        dmax = prof[-1][1]
        pts = [(Y_OUT + 0.3, cxz[1])] + [(Y_OUT - d, cxz[1] + r) for r, d in prof] + [(Y_OUT - dmax, cxz[1])]
        revolve(0, cxz[0], pts, (30.0, cxz[1]), (45.0, cxz[1]), FO.CutFeatureOperation, nm, body)
    for nm, cyz, prof in (('KneeCsC', KNEE_C, cs_hub(0)), ('KneeCsL', KNEE_L, cs_low())):
        dmax = prof[-1][1]
        pts = [(X_OUT - 0.3, cyz[1])] + [(X_OUT + d, cyz[1] + r) for r, d in prof] + [(X_OUT + dmax, cyz[1])]
        revolve(1, cyz[0], pts, (-14.0, cyz[1]), (-5.0, cyz[1]), FO.CutFeatureOperation, nm, body)

    bb = body.boundingBox
    print('bbox mm', [round(v * 10, 2) for v in bb.minPoint.asArray()], [round(v * 10, 2) for v in bb.maxPoint.asArray()])
    print('bodies', root.bRepBodies.count, 'vol mm3', round(body.volume * 1000, 1), 'faces', body.faces.count)
    app.activeViewport.fit()
