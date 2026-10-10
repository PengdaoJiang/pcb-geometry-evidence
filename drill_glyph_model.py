"""Observed glyph-encoding model; never transforms the accepted board image."""
import math

PREFIX={'CROSS':2,'CIRCLE':36,'TRIANGLE_1':3,'SQUARE':4,'RECTANGLE':4,
        'HEXAGON_X':6,'HEXAGON_Y':6,'OCTAGON':8,'OBLONG_X':38,'OBLONG_Y':38,'NULL':0}

def fit_uniform(source,target,origin,envelope=.0101,scale_limits=(.9,1.1),shift_limit=2):
    if len(source)!=len(target) or not source:return None
    ps=[];qs=[]
    for old,new in zip(source,target):
        if old['kind']!='L' or abs(old['width_mil']-new['width_mil'])>1e-8:return None
        a,b=old['a'],old['b'];c,d=new['a'],new['b']
        u=[b[k]-a[k] for k in (0,1)];v=[d[k]-c[k] for k in (0,1)]
        if sum(x*y for x,y in zip(u,v))<0:a,b=b,a
        ps.extend([[p[k]-origin[k] for k in (0,1)] for p in (a,b)])
        qs.extend([[p[k]-origin[k] for k in (0,1)] for p in (c,d)])
    pm=[sum(p[k] for p in ps)/len(ps) for k in (0,1)];qm=[sum(p[k] for p in qs)/len(qs) for k in (0,1)]
    denominator=sum((p[k]-pm[k])**2 for p in ps for k in (0,1))
    if denominator==0:return None
    scale=sum((p[k]-pm[k])*(q[k]-qm[k]) for p,q in zip(ps,qs) for k in (0,1))/denominator
    shift=[qm[k]-scale*pm[k] for k in (0,1)]
    residual=max(math.dist([scale*p[k]+shift[k] for k in (0,1)],q) for p,q in zip(ps,qs))
    # This bounded search only diagnoses near-size local encodings. Values outside
    # it are retained unmatched, never silently clipped or accepted as board fit.
    if not scale_limits[0]<=scale<=scale_limits[1] or max(map(abs,shift))>shift_limit or residual>envelope:return None
    return dict(uniform_scale=scale,local_translation_mil=shift,max_endpoint_residual_mil=residual)

OLD_PREFIX={**PREFIX,'CIRCLE':1,'OBLONG_X':4,'OBLONG_Y':4}

def outline_bounds(source):
    from document_curve_encoding import angle_on_arc
    pts=[]
    for s in source:
        pts.extend((s['a'],s['b']))
        if s['kind']=='A':
            cx,cy=s['center'];r=math.dist(s['a'],s['center'])
            for p in ((cx+r,cy),(cx-r,cy),(cx,cy+r),(cx,cy-r)):
                if angle_on_arc(p,s['a'],s['b'],s['center'],s['clockwise'],1e-9):pts.append(p)
    return [min(p[k] for p in pts) for k in (0,1)]+[max(p[k] for p in pts) for k in (0,1)]

def outline_anchor(source,semantic,origin,envelope=.0101):
    """Declared figure extent anchor; not a geometry-equivalence assertion."""
    kind=semantic['figure'];n=OLD_PREFIX[kind]
    if not n or len(source)!=n:return None
    if any(s['kind'] not in ('L','A') or abs(s['width_mil']-5.118)>1e-8 for s in source):return None
    if kind=='CIRCLE' and not(source[0]['kind']=='A' and math.dist(source[0]['a'],source[0]['b'])<1e-6):return None
    if kind not in ('CIRCLE','OBLONG_X','OBLONG_Y') and any(s['kind']!='L' for s in source):return None
    if kind not in ('CIRCLE','CROSS'):
        ends=[p for s in source for p in (s['a'],s['b'])]
        if any(sum(math.dist(p,q)<.00002 for q in ends)!=2 for p in ends):return None
    bounds=outline_bounds(source);w,h=semantic['width_height_mil'];hex_vertices=None
    if kind in ('HEXAGON_X','HEXAGON_Y'):
        start=0 if kind=='HEXAGON_X' else math.pi/2
        hex_vertices=[[origin[0]+w/2*math.cos(start+i*math.pi/3),origin[1]+h/2*math.sin(start+i*math.pi/3)] for i in range(6)]
        if any(min(math.dist(p,q) for q in hex_vertices)>envelope for s in source for p in (s['a'],s['b'])):return None
        if kind=='HEXAGON_X':h*=math.sqrt(3)/2
        else:w*=math.sqrt(3)/2
    wanted=[origin[0]-w/2,origin[1]-h/2,origin[0]+w/2,origin[1]+h/2]
    error=max(abs(a-b) for a,b in zip(bounds,wanted))
    if error>envelope:return None
    return dict(original_outline_feature_indices=[s['feature_index'] for s in source],
                original_outline_bounds_mil=bounds,predicted_source_figure_extent_mil=wanted,
                hexagon_formula_vertices_mil=hex_vertices,max_extent_residual_mil=error)
