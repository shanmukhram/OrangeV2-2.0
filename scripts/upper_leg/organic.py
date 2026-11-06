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
CELLS = [[[28.35, -50.956], [27.236, -52.131], [25.584, -52.732], [23.902, -53.122], [23.1, -51.731], [23.124, -49.975], [24.458, -49.1], [26.216, -49.1], [27.923, -49.331]], [[30.287, -52.271], [29.95, -50.733], [30.453, -49.277], [32.048, -49.1], [33.674, -49.136], [34.5, -50.38], [34.5, -52.009], [34.269, -53.586], [32.804, -54.215], [31.46, -53.401]], [[24.809, -58.051], [23.333, -57.81], [23.1, -56.217], [24.006, -55.008], [25.552, -54.446], [27.099, -53.883], [28.66, -53.378], [29.856, -54.33], [29.106, -55.631], [27.628, -56.355], [26.198, -57.168]]]

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


    # ================= ORGANIC OUTER BODY =================
    STYLE = globals().get('STYLE', 'bone')
    SPL = adsk.core.ObjectCollection

    def sk_path(axis, c, segs, name):
        # segs: list of ('L'|'S', [pts]); consecutive segments share end points; path is closed
        pl, comp = plane_at(axis, c)
        sk = root.sketches.add(pl); sk.name = name
        T = lambda uv: sk.modelToSketchSpace(P(*[cm(t) for t in to3(axis, c, uv[0], uv[1])]))
        lines = sk.sketchCurves.sketchLines; fs = sk.sketchCurves.sketchFittedSplines
        first = None; prev = None
        nseg = len(segs)
        for si, (kind, pts) in enumerate(segs):
            last_seg = si == nseg - 1
            if kind == 'L':
                for k in range(1, len(pts)):
                    if last_seg and k == len(pts) - 1:
                        lines.addByTwoPoints(prev, first); continue
                    a = prev if prev is not None else T(pts[0])
                    ln = lines.addByTwoPoints(a, T(pts[k]))
                    if first is None: first = ln.startSketchPoint
                    prev = ln.endSketchPoint
            else:
                col = SPL.create()
                col.add(prev if prev is not None else T(pts[0]))
                for k in range(1, len(pts) - 1): col.add(T(pts[k]))
                col.add(first if (last_seg and first is not None) else T(pts[-1]))
                s = fs.add(col)
                if first is None: first = s.startSketchPoint
                prev = s.endSketchPoint
        return sk, comp

    def sk_blob(axis, c, pts, name):
        pl, comp = plane_at(axis, c)
        sk = root.sketches.add(pl); sk.name = name
        col = SPL.create()
        for u, v in pts: col.add(sk.modelToSketchSpace(P(*[cm(t) for t in to3(axis, c, u, v)])))
        s = sk.sketchCurves.sketchFittedSplines.add(col); s.isClosed = True
        return sk, comp

    def ext_sk(sk, comp, c0, c1, op, name, body=None, prof='big'):
        if prof == 'big': p = bigprof(sk)
        else: p = min([sk.profiles.item(i) for i in range(sk.profiles.count)], key=lambda q: q.areaProperties().area)
        ei = ext.createInput(p, op)
        ei.setDistanceExtent(False, VI.createByReal(cm(c1 - c0) * comp))
        if body is not None: ei.participantBodies = [body]
        f = ext.add(ei); f.name = name
        return f

    J = FO.JoinFeatureOperation
    HIP_SEGS = [('L', [(7.87, -41.5), (7.87, Z_BOT), (X_OUT, Z_BOT), (X_OUT, Z_TOP)]),
                ('S', [(X_OUT, Z_TOP), (-11.4, -39.4), (-8.6, -36.6), (-5.9, -33.4), (-4.6, -29.5), (-4.75, -25.0),
                       (-3.4, -20.0), (0.0, -16.9), (3.0, -16.85), (6.2, -18.6), (7.75, -22.0), (7.1, -27.5),
                       (6.75, -32.0), (7.2, -37.5), (7.87, -41.5)])]
    KNEE_SEGS = [('L', [(22.0, Z_TOP), (Y_OUT, Z_TOP), (Y_OUT, -55.0)]),
                 ('S', [(Y_OUT, -55.0), (35.0, -56.5), (30.0, -58.3), (25.6, -60.9), (21.9, -63.6), (18.6, -65.6),
                        (15.23, -66.2), (11.9, -65.2), (9.5, -62.6), (8.88, -59.0), (9.0, -52.0), (9.6, -45.6),
                        (11.3, -41.3), (14.0, -39.4), (17.4, -39.4), (19.6, -40.3), (22.0, Z_TOP)])]
    WEB_SEGS = [('L', [(7.87, 36.0), (X_IN, 36.0), (X_IN, 23.0)]),
                ('S', [(X_IN, 23.0), (-5.8, 27.2), (-2.6, 30.4), (1.8, 32.4), (5.4, 33.1), (6.9, 34.4), (7.87, 36.0)])]

    sk, comp = sk_path(1, Y_IN, HIP_SEGS, 'HipLobe')
    f = ext_sk(sk, comp, Y_IN, Y_OUT, FO.NewBodyFeatureOperation, 'HipLobe')
    body = f.bodies.item(0); body.name = 'UpperLeg'
    sk, comp = sk_path(0, X_OUT, KNEE_SEGS, 'KneeLobe')
    ext_sk(sk, comp, X_OUT, X_IN, J, 'KneeLobe', body)
    sk, comp = sk_path(2, Z_BOT, WEB_SEGS, 'Web')
    ext_sk(sk, comp, Z_BOT, Z_TOP, J, 'Web', body)
    print('bodies after join', root.bRepBodies.count, 'lumps', body.lumps.count)
    if globals().get('STOP') == 'body':
        return

    def on(bb, ax, v):
        lo = [bb.minPoint.x, bb.minPoint.y, bb.minPoint.z][ax]; hi = [bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z][ax]
        return abs(lo - cm(v)) < 1e-4 and abs(hi - cm(v)) < 1e-4

    def fillet(col, r, name):
        for rr in (r, r * 0.8, r * 0.6):
            try:
                fi = feats.filletFeatures.createInput()
                fi.addConstantRadiusEdgeSet(col, VI.createByReal(cm(rr)), True)
                feats.filletFeatures.add(fi).name = name
                print(name, 'R', round(rr, 2), 'edges', col.count); return rr
            except Exception as e:
                print(name, 'failed at R', round(rr, 2), str(e)[:80])
        return 0

    # big soft blend where the web/panel top meets the hip plate (concave)
    col = SPL.create()
    for e in body.edges:
        bb = e.boundingBox
        if on(bb, 1, Y_IN) and on(bb, 2, Z_TOP):
            col.add(e)
    WB = globals().get('WEBBLEND', 0)
    if WB > 0: fillet(col, WB, 'WebBlend')
    # rounded outer corner where hip plate and knee panel meet
    col = SPL.create()
    for e in body.edges:
        bb = e.boundingBox
        if on(bb, 0, X_OUT) and on(bb, 1, Y_OUT): col.add(e)
    fillet(col, 3.0, 'CornerRound')
    if globals().get('STOP') == 'blend':
        return
    # soften edges face by face (one big set fails on vertex blends)
    def junction(e):
        # small web/plate junction corners stay sharp (user: they don't need fillets)
        bb = e.boundingBox
        if on(bb, 0, X_IN) or on(bb, 1, Y_IN):
            if bb.minPoint.z * 10 >= Z_BOT - 0.01 and bb.maxPoint.z * 10 <= Z_TOP + 0.01: return True
        if on(bb, 2, Z_TOP) or on(bb, 2, Z_BOT):
            if on(bb, 0, X_IN) or on(bb, 1, Y_IN): return True
        if e.length * 10 < 2.5: return True
        return False

    def soft(planes, r, name):
        col = SPL.create(); seen = set()
        for f in body.faces:
            if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType: continue
            bb = f.boundingBox
            if not any(on(bb, ax, v) for ax, v in planes): continue
            for lp in f.loops:
                if not lp.isOuter: continue
                for e in lp.edges:
                    if e.entityToken in seen: continue
                    if name != 'SoftOuter' and junction(e): continue
                    seen.add(e.entityToken); col.add(e)
        if col.count == 0: return
        if fillet(col, r, name): return
        ok = 0
        for i in range(col.count):
            one = SPL.create(); one.add(col.item(i))
            try:
                fi = feats.filletFeatures.createInput()
                fi.addConstantRadiusEdgeSet(one, VI.createByReal(cm(r)), True)
                feats.filletFeatures.add(fi).name = name + '_%d' % i; ok += 1
            except Exception:
                pass
        print(name, 'single-edge fallback ok', ok, 'of', col.count)
    soft([(0, X_OUT), (1, Y_OUT)], 1.0, 'SoftOuter')
    soft([(2, Z_BOT)], 0.8, 'SoftBottom')
    soft([(2, Z_TOP)], 0.8, 'SoftTop')

    def soft_inner():
        soft([(0, X_IN), (1, Y_IN)], 0.8, 'SoftInner')

    # ================= CUTOUTS PER STYLE =================
    def fibre(c, w, n=9):
        # tapered lens along a smooth (Catmull-Rom) centerline -> closed point list
        cs = []
        pts = [c[0]] + list(c) + [c[-1]]
        for i in range(1, len(pts) - 2):
            p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
            for k in range(n):
                t = k / float(n)
                cs.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t +
                                       (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
        cs.append(tuple(c[-1]))
        N = len(cs)
        ws = []
        for i in range(N):
            s = i / float(N - 1) * (len(w) - 1); a = int(min(s, len(w) - 2)); fr = s - a
            ws.append(w[a] * (1 - fr) + w[a + 1] * fr)
        L, R = [], []
        for i in range(N):
            a = cs[max(i - 1, 0)]; b = cs[min(i + 1, N - 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]; ln = math.hypot(tx, ty); tx, ty = tx / ln, ty / ln
            L.append((cs[i][0] - ty * ws[i], cs[i][1] + tx * ws[i])); R.append((cs[i][0] + ty * ws[i], cs[i][1] - tx * ws[i]))
        t0 = (cs[0][0] - cs[1][0], cs[0][1] - cs[1][1]); l0 = math.hypot(*t0)
        t1 = (cs[-1][0] - cs[-2][0], cs[-1][1] - cs[-2][1]); l1 = math.hypot(*t1)
        tip0 = (cs[0][0] + t0[0] / l0 * ws[0] * 0.8, cs[0][1] + t0[1] / l0 * ws[0] * 0.8)
        tip1 = (cs[-1][0] + t1[0] / l1 * ws[-1] * 0.8, cs[-1][1] + t1[1] / l1 * ws[-1] * 0.8)
        return [tip0] + L[1:-1:2] + [tip1] + R[::-1][1:-1:2]

    WINS = []
    if STYLE == 'bone':
        WINS = [[(23.0, -49.1), (28.0, -48.8), (33.0, -48.9), (35.2, -49.9), (35.0, -51.9), (32.0, -54.7),
                 (27.5, -57.5), (24.6, -59.1), (22.9, -58.1), (22.3, -54.0)]]
    elif STYLE == 'sinew':
        WINS = [fibre([(35.0, -48.8), (31.0, -49.3), (26.5, -51.2), (23.4, -54.3)], [0.5, 1.15, 1.1, 0.5]),
                fibre([(35.1, -51.9), (32.0, -53.0), (28.5, -55.0), (26.4, -57.0)], [0.45, 0.95, 0.85, 0.4])]
    elif STYLE == 'cells':
        WINS = CELLS
    for k, w in enumerate(WINS):
        sk, comp = sk_blob(0, X_OUT - 1.0, w, 'Window%d' % k)
        ext_sk(sk, comp, X_OUT - 1.0, X_IN + 1.0, FO.CutFeatureOperation, 'Window%d' % k, body, prof='small')
    if WINS:
        col = SPL.create(); seen = set()
        for e in body.edges:
            bb = e.boundingBox
            if (on(bb, 0, X_OUT) or on(bb, 0, X_IN)) and bb.minPoint.y * 10 > 21.5 and bb.maxPoint.y * 10 < 36.0 \
               and bb.minPoint.z * 10 > -60.0 and bb.maxPoint.z * 10 < -47.8:
                if e.entityToken not in seen: seen.add(e.entityToken); col.add(e)
        fillet(col, 0.7, 'WindowSoft')

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
                eb = e.boundingBox
                ua = [[eb.minPoint.y, eb.minPoint.z], [eb.minPoint.x, eb.minPoint.z], [eb.minPoint.x, eb.minPoint.y]][axis]
                ub = [[eb.maxPoint.y, eb.maxPoint.z], [eb.maxPoint.x, eb.maxPoint.z], [eb.maxPoint.x, eb.maxPoint.y]][axis]
                if lo[0] <= ua[0] * 10 and ub[0] * 10 <= hi[0] and lo[1] <= ua[1] * 10 and ub[1] * 10 <= hi[1]:
                    col.add(e)
        fi = feats.filletFeatures.createInput()
        fi.addConstantRadiusEdgeSet(col, VI.createByReal(cm(1.25)), True)
        feats.filletFeatures.add(fi).name = name
        print(name, 'edges', col.count)
    if globals().get('STOP') == 'premouth':
        return
    mouth('HipMouthR125', 1, Y_IN, HIP)
    mouth('KneeMouthR125', 0, X_IN, KNEE)
    soft_inner()

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
