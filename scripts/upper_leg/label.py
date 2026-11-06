import adsk.core, adsk.fusion, math

Y_OUT = 39.358
P = adsk.core.Point3D.create
VI = adsk.core.ValueInput
FO = adsk.fusion.FeatureOperations

# label layouts in the L1 frame (x, z on the hip plate outer face y = Y_OUT)
#   center, height mm, rotation (deg, in model x/z: 90 = text runs toward +z)
LAYOUT = {
    'tactical': dict(center=(-7.1, -35.6), height=4.5, along_z=True),
    'bone':     dict(center=(1.0, -42.3), height=4.5, along_z=False),
}
DEPTH = 0.5


def find_doc(app, vol):
    for i in range(app.documents.count):
        d = app.documents.item(i)
        des = adsk.fusion.Design.cast(d.products.itemByProductType('DesignProductType'))
        b = des.rootComponent.bRepBodies
        if b.count >= 1 and abs(b.item(0).volume * 1000 - vol) < 1:
            return d
    return None


def make_variant(design, name, mirror, kind):
    """Builds variant `name` on top of the timeline. Returns (body, timeline index before)."""
    root = design.rootComponent
    feats = root.features
    n0 = design.timeline.markerPosition
    body = root.bRepBodies.item(0)
    sz = 1.0
    if mirror:
        col = adsk.core.ObjectCollection.create(); col.add(body)
        mi = feats.mirrorFeatures.createInput(col, root.xYConstructionPlane)
        mf = feats.mirrorFeatures.add(mi)
        newb = mf.bodies.item(0)
        feats.removeFeatures.add(body)
        body = newb
        sz = -1.0
    body.name = 'UpperLeg_' + name
    lay = LAYOUT[kind]
    cx, cz = lay['center'][0], lay['center'][1] * sz
    # sketch plane at y = Y_OUT
    pi = root.constructionPlanes.createInput()
    base = root.xZConstructionPlane
    comp = round(base.geometry.normal.y)
    pi.setByOffset(base, VI.createByReal(Y_OUT / 10.0 * comp))
    pl = root.constructionPlanes.add(pi); pl.isLightBulbOn = False
    sk = root.sketches.add(pl); sk.name = 'label_' + name
    h = lay['height']
    w = h * 0.78 * len(name) + 0.6
    # text box in model coords, axis-aligned in model x/z, then map to sketch
    if lay['along_z']:
        hu, hv = h / 2 + 0.3, w / 2       # box: narrow in x, long in z
    else:
        hu, hv = w / 2, h / 2 + 0.3
    c1 = sk.modelToSketchSpace(P((cx - hu) / 10, Y_OUT / 10, (cz - hv) / 10))
    c2 = sk.modelToSketchSpace(P((cx + hu) / 10, Y_OUT / 10, (cz + hv) / 10))
    # setAsMultiLine wants an axis-aligned sketch box: build it unrotated first, then rotate
    sc = sk.modelToSketchSpace(P(cx / 10, Y_OUT / 10, cz / 10))
    # unrotated box (text runs along sketch x)
    bw, bh = w / 20.0, (h / 2 + 0.3) / 10.0
    ti = sk.sketchTexts.createInput2(name, h / 10.0)
    ti.fontName = 'Arial Black'
    ti.isHorizontalFlip = globals().get('HFLIP', False)
    ti.isVerticalFlip = globals().get('VFLIP', False)
    ti.setAsMultiLine(P(sc.x - bw, sc.y - bh, 0), P(sc.x + bw, sc.y + bh, 0),
                      adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                      adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
    st = sk.sketchTexts.add(ti)
    return body, sk, st, n0, sz


def rotate_text(st, deg):
    adsk.fusion.MultiLineTextDefinition.cast(st.definition).rotate(math.radians(deg))


def cut_text(design, body, sk, st):
    root = design.rootComponent
    ext = root.features.extrudeFeatures
    ei = ext.createInput(st, FO.CutFeatureOperation)
    pl = adsk.fusion.ConstructionPlane.cast(sk.referencePlane)
    comp = round(root.xZConstructionPlane.geometry.normal.y)
    ei.setDistanceExtent(False, VI.createByReal(-DEPTH / 10.0 * comp))
    ei.participantBodies = [body]
    f = ext.add(ei); f.name = 'LabelCut'
    return f


def text_bbox_model(st):
    bb = st.boundingBox
    return [round(v * 10, 2) for v in bb.minPoint.asArray()], [round(v * 10, 2) for v in bb.maxPoint.asArray()]
