import math,sys,unittest,warnings
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gerber_legacy_adapter import parse_legacy
from gerber_geometry import compose_objects
from shapely.geometry import Polygon

def draw(macro):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        g,_=parse_legacy('%FSLAX35Y35*%\n%MOIN*%\n%AMROTTEST*'+macro+'*%\n%ADD10ROTTEST*%\nD10*\nX100000Y200000D03*\nM02*')
    return compose_objects(g.objects,.001,dict(primitive_types=Counter(),zero_area_primitives=0))

def expected_rect(cx,cy,w,h,degrees):
    a=math.radians(degrees);c,s=math.cos(a),math.sin(a)
    # Independent transform about macro origin, THEN flash translation.
    return Polygon([(1000*(1+x*c-y*s),1000*(2+x*s+y*c)) for x,y in [(cx-w/2,cy-h/2),(cx+w/2,cy-h/2),(cx+w/2,cy+h/2),(cx-w/2,cy+h/2)]])

class MacroRotationTests(unittest.TestCase):
    def test_nonsymmetric_centerline_angles_and_offcenter(self):
        for a in (-135,-45,-30,0,30,45,90,135):
            with self.subTest(angle=a):
                g=draw(f'21,1,0.02,0.01,0.03,-0.02,{a}')
                expected=expected_rect(.03,-.02,.02,.01,a)
                self.assertLess(g.symmetric_difference(expected).area,1e-8)
    def test_opposite_angle_is_detected(self):
        a=draw('21,1,0.02,0.01,0,0,30');b=draw('21,1,0.02,0.01,0,0,-30')
        self.assertGreater(a.symmetric_difference(b).area,100)
    def test_vectorline_diagonal_is_not_reflected(self):
        a=draw('20,1,0.01,0,0,0.02,0.02,0')
        # expected_rect rotates its center; use an unrotated local center
        # on the X axis so the rotated center is (.01,.01).
        expected=expected_rect(math.sqrt(.0002),0,math.sqrt(.0008),.01,45)
        self.assertLess(a.symmetric_difference(expected).area,1e-8)
    def test_centerline_matches_explicit_outline(self):
        a=draw('21,1,0.020079,0.025201,0,0,135')
        r=expected_rect(0,0,.020079,.025201,135)
        coords=[((x-1000)/1000,(y-2000)/1000) for x,y in r.exterior.coords]
        text=','.join(str(v) for pair in coords for v in pair)
        b=draw(f'4,1,4,{text},0')
        self.assertLess(a.symmetric_difference(b).area,1e-8)

if __name__=='__main__':unittest.main()
