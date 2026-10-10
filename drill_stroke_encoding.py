"""Decode observed disconnected round-capped macro strokes without image repair."""
import math

def strokes(primitives):
    segments=[];used=set();isolated=[]
    for i,p in enumerate(primitives):
        kind=type(p).__name__
        assert kind in ('Circle','Rectangle') and p.polarity_dark,'Unqualified drill macro primitive'
        if kind!='Rectangle':continue
        assert 0<i<len(primitives)-1
        a,b=primitives[i-1],primitives[i+1]
        assert type(a).__name__==type(b).__name__=='Circle'
        assert abs(a.r-b.r)<1e-12 and abs(p.h-2*a.r)<1e-12
        ends=[(1000*(p.x+s*p.w/2*math.cos(p.rotation)),1000*(p.y+s*p.w/2*math.sin(p.rotation))) for s in (-1,1)]
        caps=[(1000*a.x,1000*a.y),(1000*b.x,1000*b.y)]
        error=min(max(math.dist(ends[j],caps[j]) for j in (0,1)),max(math.dist(ends[1-j],caps[j]) for j in (0,1)))
        assert error<1e-7,'Disconnected/corrupt stroke caps'
        used.update((i-1,i+1));segments.append(dict(primitive_index=i,a=caps[0],b=caps[1],width_mil=1000*p.h,cap_residual_mil=error))
    for i,p in enumerate(primitives):
        if type(p).__name__=='Circle' and i not in used:isolated.append(dict(primitive_index=i,xy_mil=[p.x*1000,p.y*1000],radius_mil=p.r*1000))
    return segments,isolated

def native_semantic(row,drawings):
    cs=row['native_hole_candidates']
    if cs:
        values=[dict(figure=r['instance']['drill_figure_name'],character=r['instance']['drill_char'],
                     width_height_mil=r['instance']['figure_width_height_diameter_mil'][:2]) for r in cs]
        assert all(v==values[0] for v in values)
        return values[0]
    f=drawings[row['object_index']]
    return dict(figure=f['native']['figureName'],character=f['native']['drillChar'],width_height_mil=f['precise_width_height_rotation'][:2])
