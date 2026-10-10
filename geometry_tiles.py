"""Full-domain tiled set operations. Tile boundaries are not acceptance filters."""
import math
from shapely import STRtree,get_parts,union_all
from shapely.geometry import box,GeometryCollection,MultiPolygon

def tiled_compare(left,right,band,tile_size=4000):
    assert band>0 and tile_size>4*band
    parts=[list(get_parts(g)) for g in (left,right)]
    assert all(p.geom_type=='Polygon' for side in parts for p in side)
    trees=[STRtree(side) for side in parts]
    bounds=[g.bounds for g in (left,right) if not g.is_empty]
    if not bounds:return GeometryCollection(),GeometryCollection(),[]
    x0=min(b[0] for b in bounds);y0=min(b[1] for b in bounds)
    x1=max(b[2] for b in bounds);y1=max(b[3] for b in bounds)
    # More than two buffer radii of halo: no clipped edge can affect core.
    q=16;outer=band/math.cos(math.pi/(4*q));halo=4*outer
    raw=[];separated=[];records=[]
    for ix in range(max(1,math.ceil((x1-x0)/tile_size))):
        for iy in range(max(1,math.ceil((y1-y0)/tile_size))):
            lo=(x0+ix*tile_size,y0+iy*tile_size)
            hi=(min(x1,lo[0]+tile_size),min(y1,lo[1]+tile_size))
            core=box(*lo,*hi);window=box(lo[0]-halo,lo[1]-halo,hi[0]+halo,hi[1]+halo)
            clipped=[]
            for side,tree in zip(parts,trees):
                selected=[side[int(i)] for i in tree.query(window)]
                g=MultiPolygon(selected).intersection(window) if selected else GeometryCollection()
                assert g.is_valid
                clipped.append(g)
            a,b=clipped
            d=a.symmetric_difference(b).intersection(core)
            # Polygonal buffers have a deliberately outward-inflated radius.
            # As in the untiled path, this is diagnostic, not process tolerance.
            s=a.buffer(-outer,quad_segs=q).difference(b.buffer(outer,quad_segs=q)).union(
                b.buffer(-outer,quad_segs=q).difference(a.buffer(outer,quad_segs=q))).intersection(core)
            # Intersection at tile edges may produce zero-area lines. They
            # are not image area; preserve their count explicitly in ledger.
            dp=[p for p in get_parts(d) if p.area>0];sp=[p for p in get_parts(s) if p.area>0]
            raw.extend(dp);separated.extend(sp)
            records.append(dict(tile=[ix,iy],bounds_mil=list(core.bounds),raw_area_mil2=d.area,separated_area_mil2=s.area,zero_area_parts=sum(p.area==0 for p in get_parts(d))))
            print('COMPARE_TILE '+str([ix,iy])+' raw='+str(d.area)+' separated='+str(s.area),flush=True)
    # A full union of millions of near-coincident thin slivers dominates the
    # job and is unnecessary for complete difference retention. Tile interiors
    # are disjoint. Retain their exact polygon collection, including seam
    # boundaries; component counts mean tile fragments, not connected islands.
    d=GeometryCollection(raw);s=GeometryCollection(separated)
    assert d.is_valid and s.is_valid
    assert abs(d.area-sum(r['raw_area_mil2'] for r in records))<=max(1e-6,d.area*1e-9)
    return d,s,records
