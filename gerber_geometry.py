"""Ordered Gerber image composition with explicit bounded arc approximation.

Not a certified renderer. Unsupported primitives/topologies fail closed; source
arc radial inconsistency is retained. No repair of source files or auto-alignment.
"""
import math,warnings
from collections import Counter
from gerbonara import GerberFile
from gerbonara.utils import Inch,UnknownStatementWarning
from gerbonara import graphic_primitives as gp
from shapely.geometry import Polygon,Point,LineString,GeometryCollection
from shapely import union_all,polygonize,get_parts,is_valid_reason
from gerber_legacy_adapter import parse_legacy

def warning_role(category,message):
    allowed={
        ('SyntaxWarning','Coordinate statement without explicit operation code. This is forbidden by spec.'):'LEGACY_MODAL_OPERATION',
        ('SyntaxWarning','Arc is missing I value'):'OMITTED_ZERO_I_OFFSET',
        ('SyntaxWarning','Arc is missing J value'):'OMITTED_ZERO_J_OFFSET',
        ('SyntaxWarning','D01 interpolation with a zero-size aperture. This is invalid according to spec, however, we pass through the created objects here. Note that these will not show up in e.g. SVG output since their line width is zero.'):'ZERO_AREA_DRAW_RETAINED_AS_DIAGNOSTIC',
        ('DeprecationWarning','Deprecated LN (load name) statement found. This deprecated since rev. I4 (Oct 2013).'):'DEPRECATED_LAYER_NAME_METADATA'}
    for (kind,suffix),role in allowed.items():
        if category==kind and message.endswith(suffix):return role
    raise ValueError('Unqualified parser warning '+category+': '+message)

def arc_points(p,q,c,cw,eps,stats):
    r=math.dist(p,c);rq=math.dist(q,c)
    residual=abs(r-rq);stats['max_arc_radial_inconsistency_mil']=max(stats.get('max_arc_radial_inconsistency_mil',0),residual)
    if residual>1e-7:stats['inconsistent_radius_arcs']=stats.get('inconsistent_radius_arcs',0)+1
    assert r>0 and eps>0
    a=math.atan2(p[1]-c[1],p[0]-c[0]);b=math.atan2(q[1]-c[1],q[0]-c[0])
    sweep=((a-b) if cw else (b-a))%(2*math.pi)
    if math.dist(p,q)<1e-10:sweep=2*math.pi
    # Circular chord sagitta <= eps. Exact source endpoints remain endpoints.
    step=2*math.acos(max(-1,min(1,1-min(eps,r/4)/r)))
    n=max(1,math.ceil(sweep/step));assert n<100000,'Unbounded arc subdivision'
    stats['arc_segments']=stats.get('arc_segments',0)+n
    sign=-1 if cw else 1
    return [p]+[(c[0]+r*math.cos(a+sign*sweep*i/n),c[1]+r*math.sin(a+sign*sweep*i/n)) for i in range(1,n)]+[q]

def quad_segments(radius,eps):
    if radius<=0:return 1
    angle=math.acos(max(-1,min(1,1-min(eps,radius/4)/radius)))
    return max(2,math.ceil(math.pi/(4*angle)))

def primitive_geometry(p,eps,stats,interpret_invalid=False):
    if isinstance(p,gp.Circle):
        assert p.r>=0
        return Point(1000*p.x,1000*p.y).buffer(1000*p.r,quad_segs=quad_segments(1000*p.r,eps))
    if isinstance(p,gp.Rectangle):
        # Do not use gerbonara 1.6.3 Rectangle.to_arc_poly: explicit rotation
        # is independently controlled below. Macro CenterLine/VectorLine
        # provide CCW angles (Gerber 2024.05 4.5.1.4-5), unlike the unrelated
        # utils.rotate_point helper's clockwise argument convention.
        assert p.w>=0 and p.h>=0
        co,si=math.cos(p.rotation),math.sin(p.rotation)
        return Polygon([(1000*(p.x+x*co-y*si),1000*(p.y+x*si+y*co)) for x,y in [(-p.w/2,-p.h/2),(-p.w/2,p.h/2),(p.w/2,p.h/2),(p.w/2,-p.h/2)]])
    if isinstance(p,gp.Line):
        assert p.width>=0
        a,b=(1000*p.x1,1000*p.y1),(1000*p.x2,1000*p.y2)
        center=Point(a) if a==b else LineString([a,b]);r=1000*p.width/2
        return center.buffer(r,quad_segs=quad_segments(r,eps))
    if isinstance(p,gp.Arc):
        assert p.width>=0
        a,b,c=(1000*p.x1,1000*p.y1),(1000*p.x2,1000*p.y2),(1000*p.cx,1000*p.cy)
        points=arc_points(a,b,c,p.clockwise,eps/2,stats);r=1000*p.width/2
        return LineString(points).buffer(r,quad_segs=quad_segments(r,eps/2))
    if isinstance(p,gp.ArcPoly):
        points=[]
        for a,b,(cw,c) in p.segments:
            a,b=tuple(1000*x for x in a),tuple(1000*x for x in b)
            if cw is None:part=[a,b]
            else:part=arc_points(a,b,tuple(1000*x for x in c),cw,eps,stats)
            if points:assert math.dist(points[-1],part[0])<1e-7;points.extend(part[1:])
            else:points.extend(part)
        if len(points)<3:return GeometryCollection()
        poly=Polygon(points)
        if poly.is_valid:return poly
        # Gerber permits exact doubled-back cut-ins. Do not call buffer(0)
        # or make_valid to conceal arbitrary self-intersection.
        edges=list(zip(points,points[1:]+points[:1]));edges=[(a,b) for a,b in edges if a!=b]
        counts=Counter(edges);bridge=[(a,b) for a,b in edges if counts[b,a]]
        if not bridge:
            reason=is_valid_reason(poly)
            if not interpret_invalid:raise ValueError('Non-cut-in invalid region: '+reason)
            # Explicit ERROR-bearing diagnostic, never source repair or a
            # strict geometry pass. Retain original path and both fill-rule
            # outcomes. If the rules disagree, do not choose one silently.
            linework=union_all([LineString(e) for e in edges])
            faces=list(get_parts(polygonize(list(get_parts(linework)))))
            def winding(pt):
                x,y=pt.x,pt.y;w=0
                for a,b in edges:
                    cross=(b[0]-a[0])*(y-a[1])-(x-a[0])*(b[1]-a[1])
                    if a[1]<=y<b[1] and cross>0:w+=1
                    if b[1]<=y<a[1] and cross<0:w-=1
                return w
            values=[(f,winding(f.representative_point())) for f in faces]
            odd=union_all([f for f,w in values if w%2]);nonzero=union_all([f for f,w in values if w])
            disagreement=odd.symmetric_difference(nonzero)
            rec=dict(reason=reason,source_points_mil=points,polygonized_faces=len(faces),winding_numbers=[w for f,w in values],evenodd_area_mil2=odd.area,nonzero_area_mil2=nonzero.area,fill_rule_disagreement_area_mil2=disagreement.area,status='SOURCE_GEOMETRY_ERROR_DIAGNOSTIC_ONLY')
            stats.setdefault('invalid_outline_interpretations',[]).append(rec)
            if not disagreement.is_empty:raise ValueError('Ambiguous invalid contour fill rules: '+reason)
            assert odd.is_valid and not odd.is_empty
            return odd
        for a,b in set(bridge):assert counts[a,b]==counts[b,a]==1,'Multiple/overlapping cut-in'
        remaining=[e for e in edges if e not in bridge]
        linework=union_all([LineString(e) for e in remaining]);faces=list(get_parts(polygonize(list(get_parts(linework)))))
        assert faces
        def odd(x,y):
            inside=False
            for a,b in edges:
                if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
            return inside
        selected=[f for f in faces if odd(f.representative_point().x,f.representative_point().y)]
        assert selected
        stats['explicit_cut_in_regions']=stats.get('explicit_cut_in_regions',0)+1
        return union_all(selected)
    raise ValueError('Unsupported primitive '+type(p).__name__)

def compose_objects(objects,eps,stats,interpret_invalid=False,object_sink=None):
    image=GeometryCollection();pending=[];batches=[];polarity=None
    def flush(current,shapes,groups,dark):
        if not shapes and not groups:return current
        combined=union_all([*groups,*shapes])
        return current.union(combined) if dark else current.difference(combined)
    for idx,obj in enumerate(objects):
        # An aperture's clear sub-primitives are holes in that APERTURE, not
        # a command to erase older copper behind the flash.
        primitives=list(obj.to_primitives(unit=Inch));dark=obj.polarity_dark
        shape=GeometryCollection();positive=[]
        for p in primitives:
            stats['primitive_types'][type(p).__name__]+=1
            count=len(stats.get('invalid_outline_interpretations',[]))
            try:g=primitive_geometry(p,eps,stats,interpret_invalid)
            except (ValueError,AssertionError) as e:raise ValueError(f'Object {idx} primitive {type(p).__name__}: {e}') from e
            for rec in stats.get('invalid_outline_interpretations',[])[count:]:rec['object_index']=idx
            if not g.is_valid:raise ValueError(f'Invalid primitive {idx}: '+is_valid_reason(g))
            if g.is_empty:stats['zero_area_primitives']+=1
            if p.polarity_dark==dark:positive.append(g)
            else:
                if positive:shape=shape.union(union_all(positive));positive=[]
                shape=shape.difference(g)
        if positive:shape=shape.union(union_all(positive))
        if object_sink is not None:object_sink(idx,obj,primitives,shape,dark)
        if polarity is not None and dark!=polarity:image=flush(image,pending,batches,polarity);pending=[];batches=[]
        polarity=dark
        if not shape.is_empty:pending.append(shape)
        if len(pending)>=5000:batches.append(union_all(pending));pending=[]
        if idx and idx%50000==0:print('COMPOSE_OBJECTS '+str(idx),flush=True)
    image=flush(image,pending,batches,polarity)
    assert image.is_valid
    return image

def render(path,eps,interpret_invalid=False,object_sink=None):
    stats=dict(source_path=str(path),approximation_sagitta_target_mil=eps,primitive_types=Counter(),zero_area_primitives=0)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');file,adapter=parse_legacy(path.read_text(encoding='ascii'),filename=path)
    stats['legacy_state_adapter']=adapter
    messages=[dict(category=w.category.__name__,message=str(w.message)) for w in caught]
    # Unknown records must not disappear into a nominally successful render.
    if any(issubclass(w.category,UnknownStatementWarning) for w in caught):raise ValueError('Unknown Gerber statement: '+str(messages))
    for message in messages:message['interpretation_role']=warning_role(message['category'],message['message'])
    stats.update(objects=len(file.objects),object_types=dict(Counter(type(o).__name__ for o in file.objects)),parser_warnings=messages)
    with warnings.catch_warnings(record=True) as generated:
        warnings.simplefilter('always');image=compose_objects(file.objects,eps,stats,interpret_invalid,object_sink)
    stats['conversion_warnings']=[dict(category=w.category.__name__,message=str(w.message)) for w in generated]
    if generated:raise ValueError('Unqualified conversion warnings '+str(stats['conversion_warnings']))
    stats.update(primitive_types=dict(stats['primitive_types']),area_mil2=image.area,bounds_mil=list(image.bounds),valid=image.is_valid)
    return image,stats
