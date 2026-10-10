"""Literal ODB arc vs Gerber chord association, not a fabrication tolerance.

Endpoint encoding envelopes never remove image differences. Source index,
ambiguity and unmatched candidates are retained; no snapping or source repair.
"""
import math,re

def angle_on_arc(p,a,b,c,cw,envelope):
    radius=math.dist(a,c)
    if radius<=0:return False
    if a==b:return True
    start=math.atan2(a[1]-c[1],a[0]-c[0]);end=math.atan2(b[1]-c[1],b[0]-c[0])
    theta=math.atan2(p[1]-c[1],p[0]-c[0]);sign=-1 if cw else 1
    sweep=(sign*(end-start))%(2*math.pi);travel=(sign*(theta-start))%(2*math.pi)
    margin=envelope/radius
    return travel<=sweep+margin or travel>=2*math.pi-margin

def line_distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];d=dx*dx+dy*dy
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/d)) if d else 0
    return math.dist(p,(a[0]+t*dx,a[1]+t*dy))

def association(a,b,width,source,envelope):
    if abs(width-source['width_mil'])>1e-8:return None
    x,y=source['a'],source['b']
    if source['kind']=='L':
        error=max(line_distance(p,x,y) for p in (a,b))
        return dict(kind='STRAIGHT',endpoint_error_mil=error) if error<=envelope else None
    c=source['center'];radius=math.dist(x,c)
    radial=max(abs(math.dist(p,c)-radius) for p in (a,b))
    if radial>envelope or not all(angle_on_arc(p,x,y,c,source['clockwise'],envelope) for p in (a,b)):return None
    # Also require the short circular route between the vertices to lie in the
    # source arc. Merely having two endpoints on an unrelated arc is insufficient.
    mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
    if not angle_on_arc(mid,x,y,c,source['clockwise'],envelope):return None
    sweep=abs(math.atan2(a[1]-c[1],a[0]-c[0])-math.atan2(b[1]-c[1],b[0]-c[0]))
    sweep=min(sweep,2*math.pi-sweep)
    return dict(kind='ARC_CHORD',endpoint_error_mil=radial,angle_radians=sweep,
                source_endpoint_radius_inconsistency_mil=abs(radius-math.dist(y,c)),
                nominal_sagitta_mil=radius*(1-math.cos(sweep/2)))

def read_strokes(text):
    symbols={};strokes=[];index=-1;units=0
    for raw in text.splitlines():
        line=raw.strip()
        if not line or line.startswith(('#','@','&')):continue
        if line=='UNITS=INCH':units+=1;continue
        if line.startswith('$'):
            f=line.split();assert len(f) in (2,3) and (len(f)==2 or f[2]=='I');symbols[f[0][1:]]=f[1];continue
        f=line.split(';',1)[0].split()
        if f[0] in ('P','L','A','S','T','B'):index+=1
        if f[0] not in ('L','A'):continue
        arc=f[0]=='A';symbol=symbols[f[7 if arc else 5]];m=re.fullmatch(r'r([\d.]+)',symbol);assert m
        assert f[8 if arc else 6]=='P','This positive-figure association does not qualify clear strokes'
        row=dict(feature_index=index,kind=f[0],header=line,a=tuple(1000*float(v) for v in f[1:3]),
                 b=tuple(1000*float(v) for v in f[3:5]),width_mil=float(m[1]))
        if arc:row.update(center=tuple(1000*float(v) for v in f[5:7]),clockwise=f[10]=='Y')
        strokes.append(row)
    assert units==1
    return strokes,index+1

def macro_segments(primitives):
    """Only the observed alternating round-cap/stroke macro grammar."""
    assert len(primitives)>=3 and len(primitives)%2==1
    segments=[]
    for i in range(0,len(primitives)-2,2):
        a,r,b=primitives[i:i+3]
        assert type(a).__name__==type(b).__name__=='Circle' and type(r).__name__=='Rectangle'
        assert a.polarity_dark and b.polarity_dark and r.polarity_dark
        assert abs(a.r-b.r)<1e-12 and abs(r.h-2*a.r)<1e-12
        endpoints=[(1000*(r.x+sign*r.w/2*math.cos(r.rotation)),1000*(r.y+sign*r.w/2*math.sin(r.rotation))) for sign in (-1,1)]
        caps=[(1000*a.x,1000*a.y),(1000*b.x,1000*b.y)]
        error=min(max(math.dist(endpoints[j],caps[j]) for j in (0,1)),max(math.dist(endpoints[1-j],caps[j]) for j in (0,1)))
        assert error<1e-7,'Cap/rectangle endpoint mismatch'
        segments.append(dict(a=caps[0],b=caps[1],width_mil=1000*r.h,cap_rectangle_residual_mil=error))
    return segments
