"""Directed set coverage without erosion: never erase thin input features."""
import math
from shapely import STRtree,get_parts
from shapely.geometry import box,GeometryCollection,MultiPolygon

def directed_coverage(left,right,radius,tile_size=4000):
    assert radius>0 and tile_size>4*radius
    parts=[list(get_parts(g)) for g in (left,right)]
    assert all(p.geom_type=='Polygon' for side in parts for p in side)
    trees=[STRtree(side) for side in parts]
    bounds=[g.bounds for g in (left,right) if not g.is_empty]
    if not bounds:return GeometryCollection(),GeometryCollection(),[],radius
    x0=min(b[0] for b in bounds);y0=min(b[1] for b in bounds)
    x1=max(b[2] for b in bounds);y1=max(b[3] for b in bounds)
    q=16;outer=radius/math.cos(math.pi/(4*q));halo=4*outer
    first=[];second=[];records=[]
    for ix in range(max(1,math.ceil((x1-x0)/tile_size))):
        for iy in range(max(1,math.ceil((y1-y0)/tile_size))):
            lo=(x0+ix*tile_size,y0+iy*tile_size)
            hi=(min(x1,lo[0]+tile_size),min(y1,lo[1]+tile_size))
            core=box(*lo,*hi);window=box(lo[0]-halo,lo[1]-halo,hi[0]+halo,hi[1]+halo)
            clipped=[]
            for side,tree in zip(parts,trees):
                selected=[side[int(i)] for i in tree.query(window)]
                shape=MultiPolygon(selected).intersection(window) if selected else GeometryCollection()
                assert shape.is_valid;clipped.append(shape)
            a,b=clipped
            # Critically, there is no a.buffer(-radius) or b.buffer(-radius).
            l=a.difference(b.buffer(outer,quad_segs=q)).intersection(core)
            r=b.difference(a.buffer(outer,quad_segs=q)).intersection(core)
            first.extend(p for p in get_parts(l) if p.area>0)
            second.extend(p for p in get_parts(r) if p.area>0)
            records.append(dict(tile=[ix,iy],bounds_mil=list(core.bounds),
                left_uncovered_area_mil2=l.area,right_uncovered_area_mil2=r.area,
                zero_area_parts=sum(p.area==0 for g in (l,r) for p in get_parts(g))))
            print('COVERAGE_TILE '+str([ix,iy])+' left='+str(l.area)+' right='+str(r.area),flush=True)
    a,b=GeometryCollection(first),GeometryCollection(second)
    assert a.is_valid and b.is_valid
    for shape,field in [(a,'left_uncovered_area_mil2'),(b,'right_uncovered_area_mil2')]:
        assert abs(shape.area-sum(r[field] for r in records))<=max(1e-6,shape.area*1e-9)
    return a,b,records,outer
