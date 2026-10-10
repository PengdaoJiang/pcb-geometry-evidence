"""Exact rational intersections of retained straight-edged region polygons."""
import argparse,json,shutil
from collections import Counter
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
from analyze_method import BASE,sha

def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def signed_area2(p):return sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(p,p[1:]+p[:1]))
def edges(p):return list(zip(p,p[1:]+p[:1]))
def inside_triangle(p,a,b,c):return min(cross(a,b,p),cross(b,c,p),cross(c,a,p))>=0

def triangulate(points):
    p=[tuple(F(str(v)) for v in point) for point in points]
    if p[0]==p[-1]:p.pop()
    assert len(set(p))==len(p)
    # Collinear middle vertices are redundant, not a geometric repair.
    changed=True
    while changed and len(p)>3:
        changed=False
        for i in range(len(p)):
            a,b,c=p[i-1],p[i],p[(i+1)%len(p)]
            if cross(a,b,c)==0:
                assert all(min(a[k],c[k])<=b[k]<=max(a[k],c[k]) for k in (0,1))
                p.pop(i);changed=True;break
    if signed_area2(p)<0:p.reverse()
    expected=signed_area2(p);assert expected>0
    triangles=[]
    while len(p)>3:
        for i,b in enumerate(p):
            a,c=p[i-1],p[(i+1)%len(p)]
            if cross(a,b,c)<=0:continue
            if any(inside_triangle(q,a,b,c) for j,q in enumerate(p) if j not in ((i-1)%len(p),i,(i+1)%len(p))):continue
            triangles.append([a,b,c]);p.pop(i);break
        else:raise AssertionError('No ear: self-intersection or unsupported topology')
    triangles.append(p)
    assert all(signed_area2(t)>0 for t in triangles)
    assert sum(signed_area2(t) for t in triangles)==expected
    return triangles

def intersect_convex(subject,clip):
    p=subject[:]
    for a,b in edges(clip):
        out=[]
        if not p:break
        for c,d in edges(p):
            sc,sd=cross(a,b,c),cross(a,b,d)
            if (sc>=0)!=(sd>=0):
                t=sc/(sc-sd);out.append(tuple(c[k]+t*(d[k]-c[k]) for k in (0,1)))
            if sd>=0:out.append(d)
        p=out
    return abs(signed_area2(p))/2 if len(p)>=3 else F(0)

def overlap(a,b):return sum((intersect_convex(x,y) for x in a for y in b),F(0))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',default='region_geometry_analysis_v1');parser.add_argument('--label',default='region_overlap_exact_v1');args=parser.parse_args()
    assert all(Path(v).name==v for v in (args.source,args.label))
    source=BASE/args.source
    polygons=json.loads((source/'polygons.json').read_text());members={r['member']:r for r in json.loads((source/'members.json').read_text())}
    assert not json.loads((source/'holes.json').read_text())
    triangles={};areas=[]
    for p in polygons:
        assert all(v[1]==0 for v in p['vertices'])
        triangles[p['member']]=triangulate([v[0] for v in p['vertices']])
        exact=sum(signed_area2(t)/2 for t in triangles[p['member']])
        areas.append(dict(member=p['member'],region=p['region'],exact_area_mil2=str(exact),printed_api_area_mil2=p['area_mil2'],printed_minus_exact_mil2=float(F(str(p['area_mil2']))-exact)))
    pairs=[]
    for a,b in combinations(polygons,2):
        layer=members[a['member']]['object']['layer']
        if a['region']==b['region'] or layer!=members[b['member']]['object']['layer']:continue
        def bbox(poly):
            vs=[v[0] for v in poly['vertices']]
            return [[min(v[i] for v in vs) for i in (0,1)],[max(v[i] for v in vs) for i in (0,1)]]
        aa,bb=bbox(a),bbox(b)
        box_overlap=min(aa[1][0],bb[1][0])>max(aa[0][0],bb[0][0]) and min(aa[1][1],bb[1][1])>max(aa[0][1],bb[0][1])
        amount=overlap(triangles[a['member']],triangles[b['member']]) if box_overlap else F(0)
        pairs.append(dict(a=a['member'],b=b['member'],region_a=a['region'],region_b=b['region'],layer=layer,
            overlap_area_mil2=str(amount),overlap_area_float_mil2=float(amount),positive_interior_overlap=amount>0))
    summary=dict(status='EXACT_PRINTED_POLYGON_OVERLAP_NOT_PRIORITY_SEMANTICS',regions=4,polygons=len(polygons),
        triangles=sum(map(len,triangles.values())),different_region_same_layer_pairs=len(pairs),
        positive_area_pairs=sum(r['positive_interior_overlap'] for r in pairs),
        positive_area_region_pairs=dict(Counter('|'.join(sorted((r['region_a'],r['region_b']))) for r in pairs if r['positive_interior_overlap'])),
        boundary='Exact rational arithmetic on retained printed vertices; no arc, holes, tolerance expansion or unknown topology accepted. Printed API areas have limited display precision and are kept separately. Zero interior area does not exclude shared edges. Geometry alone cannot select the winning rule.',
        inputs=[dict(path=str(source/name),sha256=sha(source/name)) for name in ['polygons.json','members.json','holes.json']])
    out=BASE/args.label;out.mkdir(exist_ok=False)
    for name,obj in [('summary.json',summary),('pairs.json',pairs),('areas.json',areas)]:
        (out/name).write_text(json.dumps(obj,indent=2))
    shutil.copy2(Path(__file__),out/Path(__file__).name)
    (out/'manifest.json').write_text(json.dumps([dict(path=f.name,bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(out.iterdir())],indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
