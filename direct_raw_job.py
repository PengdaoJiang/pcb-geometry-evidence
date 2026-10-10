import gzip,hashlib,json,math

from pathlib import Path

from shapely import from_wkb,to_wkb,get_parts,STRtree

from shapely.geometry import box,GeometryCollection,MultiPolygon

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def raw_tiled(a,b,tile=4000):
    parts=[list(get_parts(g)) for g in (a,b)];trees=[STRtree(p) for p in parts]
    assert all(g.geom_type=='Polygon' for ps in parts for g in ps)
    bounds=[g.bounds for g in (a,b) if not g.is_empty]
    if not bounds:return GeometryCollection(),[]
    x0,y0=min(b[0] for b in bounds),min(b[1] for b in bounds)
    x1,y1=max(b[2] for b in bounds),max(b[3] for b in bounds);out=[];rows=[]
    for i in range(max(1,math.ceil((x1-x0)/tile))):
        for j in range(max(1,math.ceil((y1-y0)/tile))):
            core=box(x0+i*tile,y0+j*tile,min(x1,x0+(i+1)*tile),min(y1,y0+(j+1)*tile));gs=[]
            for ps,tr in zip(parts,trees):
                chosen=[ps[int(k)] for k in tr.query(core)]
                gs.append(MultiPolygon(chosen).intersection(core) if chosen else GeometryCollection())
            diff=gs[0].symmetric_difference(gs[1]);assert diff.is_valid
            elements=list(get_parts(diff));out.extend(g for g in elements if g.area>0)
            rows.append(dict(tile=[i,j],bounds_mil=list(core.bounds),area_mil2=diff.area,zero_area_parts=sum(g.area==0 for g in elements)))
            print('RAW_TILE '+str([i,j])+' '+str(diff.area),flush=True)
    result=GeometryCollection(out);assert result.is_valid
    assert math.isclose(result.area,sum(r['area_mil2'] for r in rows),rel_tol=1e-9,abs_tol=1e-6)
    return result,rows
