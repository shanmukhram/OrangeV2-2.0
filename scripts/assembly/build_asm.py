import adsk.core, adsk.fusion, json

SP = r'C:/Users/admin/Desktop/HEXA-Orange/scripts/assembly'
V2 = r'C:/Users/admin/Desktop/HEXA-Orange/output/v2'
UP = V2 + '/Orange_UpperLeg_Bone_v2/Orange_UpperLeg_Bone_MultiHole/Orange_UpperLeg_Bone_MultiHole_v2_%s.step'
LOW = V2 + '/Orange_LowerLeg_v2_%s.step'
P3 = adsk.core.Point3D.create
V3 = adsk.core.Vector3D.create


def mat(T):
    m = adsk.core.Matrix3D.create()
    a = []
    for r in range(4):
        for c in range(4):
            v = T[r][c]
            if c == 3 and r < 3: v = v / 10.0
            a.append(v)
    m.setWithArray(a)
    return m


def import_step(app, root, path, name, T):
    im = app.importManager
    n0 = root.occurrences.count
    im.importToTarget(im.createSTEPImportOptions(path), root)
    occ = root.occurrences.item(root.occurrences.count - 1)
    assert root.occurrences.count == n0 + 1, 'import added %d occurrences' % (root.occurrences.count - n0)
    occ.component.name = name
    if T is not None:
        occ.transform2 = mat(T)
    return occ


def servo_component(root):
    tbm = adsk.fusion.TemporaryBRepManager.get()
    def box(x0, x1, y0, y1, z0, z1):
        c = P3((x0 + x1) / 20.0, (y0 + y1) / 20.0, (z0 + z1) / 20.0)
        ob = adsk.core.OrientedBoundingBox3D.create(c, V3(1, 0, 0), V3(0, 1, 0), (x1 - x0) / 10.0, (y1 - y0) / 10.0, (z1 - z0) / 10.0)
        return tbm.createBox(ob)
    # local frame: origin = shaft axis on the servo top face, +X toward the shaft end, +Z up (shaft direction)
    body = box(-16.6, 6.3, -6.2, 6.2, -24.5, 0.0)
    tabs = box(-21.4, 11.1, -6.2, 6.2, -8.26, -5.76)
    shaft = tbm.createCylinderOrCone(P3(0, 0, 0), 0.24, P3(0, 0, 0.28), 0.24)
    tbm.booleanOperation(body, tabs, adsk.fusion.BooleanTypes.UnionBooleanType)
    tbm.booleanOperation(body, shaft, adsk.fusion.BooleanTypes.UnionBooleanType)
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = 'MG90S'
    comp.bRepBodies.add(body).name = 'MG90S envelope'
    return occ


def build():
    app = adsk.core.Application.get()
    poses = json.load(open(SP + '/poses.json'))
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.DirectDesignType
    root = design.rootComponent
    body = import_step(app, root, V2 + '/Orange_Assembly_v2.step', 'Body_v2', None)
    # swap in the widened base (brackets 4.5 mm further out each side)
    for i in range(body.childOccurrences.count):
        o = body.childOccurrences.item(i)
        if o.name.lower().startswith('base'): o.isLightBulbOn = False; print('hid', o.name)
    import_step(app, root, SP + '/base_wide.step', 'Base_wide', None)
    s0 = servo_component(root)
    scomp = s0.component
    occs = {}
    for leg in ('L1', 'L2', 'R1', 'R2'):
        p = poses[leg]
        occs['up_' + leg] = import_step(app, root, UP % leg, 'UpperLeg_' + leg, p['upper'])
        occs['low_' + leg] = import_step(app, root, LOW % p['lower_name'], 'LowerLeg_' + p['lower_name'], p['lower'])
        occs['hip_' + leg] = root.occurrences.addExistingComponent(scomp, mat(p['hip_servo']))
        occs['knee_' + leg] = root.occurrences.addExistingComponent(scomp, mat(p['knee_servo']))
    # the template occurrence sits at the origin; remove it (the component stays referenced by the 8 copies)
    s0.deleteMe()
    app.activeViewport.fit()
    print('top-level occurrences', root.occurrences.count)
    for i in range(body.childOccurrences.count):
        print('  body part:', body.childOccurrences.item(i).component.name)
    return design, body, occs
