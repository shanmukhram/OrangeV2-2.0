import os
try:  # repo root, found from this file's location
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
except NameError:  # exec'd inside Fusion: set ORANGE_ROOT to the repo folder
    ROOT = os.environ.get('ORANGE_ROOT', os.getcwd())
import adsk.core, adsk.fusion, os

SP = os.path.join(ROOT, 'scripts/upper_leg')
OUT = os.path.join(ROOT, 'output')

# design key -> (label layout kind, folder, file base)
DESIGNS = {
    'tactical': ('tactical', OUT + '/Orange_UpperLeg_Tactical_v2', 'Orange_UpperLeg_Tactical_v2'),
    'bone':     ('bone', OUT + '/Orange_UpperLeg_Bone_v2/Orange_UpperLeg_Bone_SingleHole', 'Orange_UpperLeg_Bone_SingleHole_v2'),
    'sinew':    ('bone', OUT + '/Orange_UpperLeg_Bone_v2/Orange_UpperLeg_Bone_TwoHoles', 'Orange_UpperLeg_Bone_TwoHoles_v2'),
    'cells':    ('bone', OUT + '/Orange_UpperLeg_Bone_v2/Orange_UpperLeg_Bone_MultiHole', 'Orange_UpperLeg_Bone_MultiHole_v2'),
}
# leg -> mirrored (L2 and R1 are L1 mirrored in z; R2 is the same shape as L1)
LEGS = [('L1', False), ('L2', True), ('R1', True), ('R2', False)]
# text rotation (deg) so it reads correctly from outside, hip end up
ROT = {('tactical', False): 270, ('tactical', True): 90, ('bone', False): 180, ('bone', True): 0}


def kind_of(des):
    r = des.rootComponent
    if r.sketches.itemByName('PanelWindow1') and not r.sketches.itemByName('Web'): return 'tactical'
    if r.sketches.itemByName('Web'):
        n = sum(1 for k in range(4) if r.sketches.itemByName('Window%d' % k))
        return {1: 'bone', 2: 'sinew', 3: 'cells'}.get(n)
    return None


def base_marker(des):
    # timeline index of the first label item (construction plane right before 'label_*' sketch), else count
    tl = des.timeline
    for i in range(tl.count):
        e = tl.item(i).entity
        if isinstance(e, adsk.fusion.Sketch) and e.name.startswith('label_'):
            return i - 1
        if isinstance(e, adsk.fusion.MirrorFeature) or isinstance(e, adsk.fusion.RemoveFeature):
            return i
    return tl.count


def run_all(only=None):
    app = adsk.core.Application.get()
    L = {'__name__': 'label'}
    exec(open(SP + '/label.py').read(), L)
    docs = {}
    for i in range(app.documents.count):
        d = app.documents.item(i)
        des = adsk.fusion.Design.cast(d.products.itemByProductType('DesignProductType'))
        k = kind_of(des)
        if k: docs[k] = d
    report = []
    for key, (layout, folder, base) in DESIGNS.items():
        if only and key not in only: continue
        d = docs[key]; d.activate()
        design = adsk.fusion.Design.cast(app.activeProduct)
        tl = design.timeline
        m0 = base_marker(design)
        tl.markerPosition = m0; tl.deleteAllAfterMarker()
        v0 = design.rootComponent.bRepBodies.item(0).volume * 1000
        os.makedirs(folder, exist_ok=True)
        for leg, mir in LEGS:
            body, sk, st, n0, sz = L['make_variant'](design, leg, mir, layout)
            L['rotate_text'](st, ROT[(layout, mir)])
            L['cut_text'](design, body, sk, st)
            root = design.rootComponent
            nb = root.bRepBodies.count
            em = design.exportManager
            stl = folder + '/' + base + '_' + leg + '.stl'
            o = em.createSTLExportOptions(body, stl)
            o.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            em.execute(o)
            em.execute(em.createSTEPExportOptions(folder + '/' + base + '_' + leg + '.step', root))
            bb = body.boundingBox
            report.append((key, leg, nb, round(body.volume * 1000, 1), round(bb.minPoint.z * 10, 2), round(bb.maxPoint.z * 10, 2)))
            tl.markerPosition = m0; tl.deleteAllAfterMarker()
        # leave the design showing the L1 label (this is what gets saved to Fusion)
        body, sk, st, n0, sz = L['make_variant'](design, 'L1', False, layout)
        L['rotate_text'](st, ROT[(layout, False)])
        L['cut_text'](design, body, sk, st)
        print(key, 'base vol', round(v0, 1), 'final L1 vol', round(body.volume * 1000, 1))
    for r in report: print(r)
