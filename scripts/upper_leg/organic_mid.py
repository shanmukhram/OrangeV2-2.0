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
