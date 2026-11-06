import json, ast, sys
SP = sys.argv[1]
OLD = sys.argv[2]
old = open(OLD).read().split('\n')
mid = open(SP + '/organic_mid.py').read().rstrip('\n').split('\n')
cells = json.load(open(SP + '/cells.json'))
head = old[0:28] + ['CELLS = ' + json.dumps(cells)]
helpers = old[30:139]
func = old[160:207]
tail = old[259:283]
src = '\n'.join(head + [''] + helpers + [''] + mid + [''] + func + ['    soft_inner()', ''] + tail) + '\n'
OLDSEL = """            for e in f.edges:
                q = e.pointOnEdge
                uv = [[q.y, q.z], [q.x, q.z], [q.x, q.y]][axis]
                if lo[0] <= uv[0] * 10 <= hi[0] and lo[1] <= uv[1] * 10 <= hi[1]:
                    col.add(e)"""
NEWSEL = """            for e in f.edges:
                eb = e.boundingBox
                ua = [[eb.minPoint.y, eb.minPoint.z], [eb.minPoint.x, eb.minPoint.z], [eb.minPoint.x, eb.minPoint.y]][axis]
                ub = [[eb.maxPoint.y, eb.maxPoint.z], [eb.maxPoint.x, eb.maxPoint.z], [eb.maxPoint.x, eb.maxPoint.y]][axis]
                if lo[0] <= ua[0] * 10 and ub[0] * 10 <= hi[0] and lo[1] <= ua[1] * 10 and ub[1] * 10 <= hi[1]:
                    col.add(e)"""
assert OLDSEL in src
src = src.replace(OLDSEL, NEWSEL)
M = "    mouth('HipMouthR125', 1, Y_IN, HIP)"
assert M in src
src = src.replace(M, "    if globals().get('STOP') == 'premouth':\n        return\n" + M)
ast.parse(src)
open(SP + '/organic.py', 'w').write(src)
print('ok', src.count('\n'), 'lines')
print('helpers first/last:', helpers[0].strip()[:40], '|', helpers[-1].strip()[:40])
print('func first/last:', func[0].strip()[:50], '|', func[-1].strip()[:50])
print('tail first/last:', tail[0].strip()[:50], '|', tail[-1].strip()[:50])
