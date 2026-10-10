"""Strict bounded ODB feature geometry for the observed ZCU111 source dialect.

Independent of CAM import/export and Gerber parsing. Curves are still polygon
approximations. Unsupported syntax, invalid contours, units or transformations
fail closed; never repair source topology. ODB++ 2024 spec pp. 39, 167-180,
187-188, 203 supplies the semantics. This is not a general ODB signoff engine.
"""
from collections import Counter
import math
import re
from shapely import union_all, is_valid_reason
from shapely.affinity import translate, rotate, scale
from shapely.geometry import Point, LineString, Polygon, box, GeometryCollection
from gerber_geometry import arc_points, quad_segments

NUMBER = r'(?:\d+(?:\.\d*)?|\.\d+)'


def valid(g, label):
    if not g.is_valid: raise ValueError(label + ': ' + is_valid_reason(g))
    return g


def circular(radius, eps):
    if radius < 0: raise ValueError('Negative radius')
    return Point(0, 0).buffer(radius, quad_segs=quad_segments(radius, eps))


def standard_symbol(name, eps):
    """Local mil coordinates; return None only for a nonstandard symbol name."""
    m = re.fullmatch(r'([rs])(' + NUMBER + ')', name)
    if m:
        d = float(m[2])
        return circular(d / 2, eps) if m[1] == 'r' else box(-d/2, -d/2, d/2, d/2)
    m = re.fullmatch(r'(rect|oval)(' + NUMBER + ')x(' + NUMBER + r')(?:x([rc])(' + NUMBER + r')(?:x([1234]+))?)?', name)
    if not m: return None
    kind, w, h, rounding, r, corners = m.groups(); w, h = float(w), float(h)
    if min(w,h) <= 0: raise ValueError('Nonpositive nonround aperture')
    if kind == 'oval':
        if rounding: raise ValueError('Unsupported oval suffix')
        radius = min(w,h)/2
        endpoints = [(-(w-h)/2,0),((w-h)/2,0)] if w>=h else [(0,-(h-w)/2),(0,(h-w)/2)]
        path = Point(0,0) if w==h else LineString(endpoints)
        return path.buffer(radius,quad_segs=quad_segments(radius,eps))
    g = box(-w/2,-h/2,w/2,h/2)
    if rounding:
        r = float(r); corners = corners or '1234'
        if r<=0 or r>min(w,h)/2+1e-12 or len(set(corners))!=len(corners):
            raise ValueError('Unsupported corner size or duplicate corners')
        # Independent constructive definition: remove only each corner square
        # outside its radius circle (rounded), or the corner triangle (chamfer).
        for c in corners:
            sx,sy = {'1':(1,1),'2':(-1,1),'3':(-1,-1),'4':(1,-1)}[c]
            x,y = sx*w/2,sy*h/2; cx,cy = x-sx*r,y-sy*r
            if rounding=='c':
                cut = Polygon([(x,y),(cx,y),(x,cy)])
            else:
                square = box(min(x,cx),min(y,cy),max(x,cx),max(y,cy))
                cut = square.difference(translate(circular(r,eps),cx,cy))
            g = g.difference(cut)
    return valid(g,'standard '+name)


def orient_symbol(g, orientation):
    if len(orientation)==1 and orientation[0] in list('01234567'):
        n=int(orientation[0]); angle=90*(n%4); mirror=n>=4
    elif len(orientation)==2 and orientation[0] in ('8','9'):
        angle=float(orientation[1]); mirror=orientation[0]=='9'
    else: raise ValueError('Unsupported ODB orientation '+repr(orientation))
    # ODB clockwise rotation, then mirror in x-axis. Not Gerber's convention.
    if angle: g=rotate(g,-angle,origin=(0,0))
    if mirror: g=scale(g,xfact=1,yfact=-1,origin=(0,0))
    return g


class Renderer:
    def __init__(self, eps, user_symbols=None, feature_sink=None):
        if not 0<eps<=.01: raise ValueError('Invalid approximation target')
        self.eps=eps; self.user_symbols=user_symbols or {}; self.cache={}; self.stack=[]; self.feature_sink=feature_sink
        self.stats=dict(approximation_target_mil=eps,features=Counter(),symbols=Counter(),
                        orientations=Counter(),polarities=Counter(),zero_area_features=0,
                        surface_islands=0,surface_holes=0,custom_symbol_files={},max_arc_radial_inconsistency_mil=0)

    def symbol(self,name):
        if name in self.cache: return self.cache[name]
        g=standard_symbol(name,self.eps)
        if g is None:
            if name not in self.user_symbols: raise ValueError('Unknown symbol '+name)
            if name in self.stack or len(self.stack)>=4: raise ValueError('Recursive symbol dependency')
            self.stack.append(name)
            try:
                g,n=self.features(self.user_symbols[name],label='symbol '+name)
                self.stats['custom_symbol_files'][name]=n
            finally: self.stack.pop()
        valid(g,'aperture '+name); self.cache[name]=g
        return g

    def stroke(self,f,symbols,arc):
        name=symbols[f[7 if arc else 5]]
        m=re.fullmatch('r('+NUMBER+')',name)
        if not m: raise ValueError('Only round line/arc stroke aperture qualified: '+name)
        r=float(m[1])/2
        if arc:
            if len(f)!=11 or f[10] not in ('Y','N'): raise ValueError('Invalid arc record')
            a,b,c=[tuple(1000*float(v) for v in f[i:i+2]) for i in (1,3,5)]
            points=arc_points(a,b,c,f[10]=='Y',self.eps/2,self.stats)
            center=LineString(points); eps=self.eps/2
        else:
            if len(f)!=8: raise ValueError('Invalid line record')
            a,b=[tuple(1000*float(v) for v in f[i:i+2]) for i in (1,3)]
            center=Point(a) if a==b else LineString([a,b]);eps=self.eps
        return center.buffer(r,quad_segs=quad_segments(r,eps))

    def surface(self, contours):
        islands=[]; holes=[]
        for kind,points in contours:
            if len(points)<4 or points[0]!=points[-1]: raise ValueError('Unclosed/short surface polygon')
            g=valid(Polygon(points),'surface '+kind)
            if g.is_empty or g.area==0: raise ValueError('Degenerate surface contour')
            (islands if kind=='I' else holes).append(g)
        if not islands: raise ValueError('Surface without island')
        positive=valid(union_all(islands),'island union')
        if holes:
            negative=valid(union_all(holes),'hole union')
            # Do not silently clip an escaped hole or repair its topology.
            outside=negative.difference(positive)
            if not outside.is_empty and outside.area>0:
                raise ValueError('Surface hole outside polygonized islands; area='+str(outside.area))
            positive=positive.difference(negative)
        self.stats['surface_islands']+=len(islands);self.stats['surface_holes']+=len(holes)
        return valid(positive,'surface result')

    def features(self,text,label='layer'):
        symbols={};units=None;expected=None;count=0;image=GeometryCollection();pending=[];groups=[];polarity=None
        contours=None; points=None; kind=None; surface_polarity=None; start_line=None; feature_header=None
        def flush():
            nonlocal image,pending,groups
            if not pending and not groups:return
            combined=union_all([*groups,*pending]);valid(combined,'feature union')
            image=image.union(combined) if polarity=='P' else image.difference(combined)
            pending=[];groups=[]
        def emit(g,p):
            nonlocal polarity,pending
            if p not in ('P','N'):raise ValueError('Unknown feature polarity')
            valid(g,'feature')
            if self.feature_sink is not None:
                self.feature_sink(dict(label=label,feature_index=count-1,start_line=start_line,header=feature_header),g,p)
            self.stats['polarities'][p]+=1
            if g.is_empty:self.stats['zero_area_features']+=1
            if polarity is not None and p!=polarity:flush()
            polarity=p;pending.append(g)
            if len(pending)>=2048:groups.append(union_all(pending));pending=[]
        for lineno,raw in enumerate(text.splitlines(),1):
            s=raw.strip()
            if not s or s.startswith('#'):continue
            try:
                if s.startswith('UNITS='):
                    if units is not None or s!='UNITS=INCH':raise ValueError('Unexpected units')
                    units='INCH';continue
                if s.startswith('$'):
                    f=s.split()
                    if len(f) not in (2,3) or f[0][1:] in symbols:raise ValueError('Bad symbol declaration')
                    if len(f)==3 and f[2]!='I':raise ValueError('Only explicit imperial symbol units qualified')
                    symbols[f[0][1:]]=f[1];continue
                if s.startswith(('@','&')) or re.fullmatch(r'ID=\d+',s):continue
                f=s.split(';',1)[0].split();code=f[0]
                if code=='F':
                    if len(f)!=2 or expected is not None:raise ValueError('Invalid feature count')
                    expected=int(f[1]);continue
                if units!='INCH':raise ValueError('Missing units before geometry')
                if code=='OB':
                    if contours is None or points is not None or len(f)!=4 or f[3] not in ('I','H'):raise ValueError('Invalid OB')
                    points=[tuple(1000*float(v) for v in f[1:3])];kind=f[3];continue
                if code in ('OS','OC'):
                    if points is None:raise ValueError('Segment outside contour')
                    q=tuple(1000*float(v) for v in f[1:3])
                    if code=='OS':
                        if len(f)!=3:raise ValueError('Invalid OS')
                        points.append(q)
                    else:
                        if len(f)!=6 or f[5] not in ('Y','N'):raise ValueError('Invalid OC')
                        c=tuple(1000*float(v) for v in f[3:5])
                        points.extend(arc_points(points[-1],q,c,f[5]=='Y',self.eps,self.stats)[1:])
                    continue
                if code=='OE':
                    if f!=['OE'] or points is None:raise ValueError('Invalid OE')
                    contours.append((kind,points));points=None;continue
                if code=='SE':
                    if f!=['SE'] or contours is None or points is not None:raise ValueError('Invalid SE')
                    emit(self.surface(contours),surface_polarity);contours=None;continue
                if contours is not None:raise ValueError('Feature interrupts surface')
                if code not in ('P','L','A','S'):raise ValueError('Unsupported directive '+code)
                count+=1;self.stats['features'][code]+=1;start_line=lineno;feature_header=s
                if code=='S':
                    if len(f)!=3:raise ValueError('Invalid surface header')
                    contours=[];surface_polarity=f[1];continue
                if code=='P':
                    if len(f) not in (7,8) or f[3]=='-1':raise ValueError('Resizing or pad syntax not qualified')
                    name=symbols[f[3]];self.stats['symbols'][name]+=1;self.stats['orientations'][' '.join(f[6:])]+=1
                    g=orient_symbol(self.symbol(name),f[6:]);g=translate(g,1000*float(f[1]),1000*float(f[2]));p=f[4]
                else:g=self.stroke(f,symbols,code=='A');p=f[8 if code=='A' else 6]
                emit(g,p)
            except Exception as exc:
                raise ValueError(f'{label} line {lineno}, feature {count-1}, start {start_line}: {exc}; source={s[:160]}') from exc
        if contours is not None or points is not None:raise ValueError('Unterminated surface')
        if units!='INCH':raise ValueError('Missing units')
        if expected is not None and expected!=count:raise ValueError(f'Feature count mismatch {expected}/{count}')
        flush();return valid(image,label+' image'),count
