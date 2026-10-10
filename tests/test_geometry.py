import math,sys,unittest
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gerber_geometry import primitive_geometry,compose_objects,render,arc_points,warning_role
from gerbonara import graphic_primitives as gp
from gerbonara import GerberFile
from shapely.geometry import Point,Polygon
from geometry_tiles import tiled_compare

def stats():return dict(primitive_types=Counter(),zero_area_primitives=0)
def image(body,aps='%ADD10C,0.020*%\n%ADD11C,0.010*%'):
    return compose_objects(GerberFile.from_string('%FSLAX35Y35*%\n%MOIN*%\n'+aps+'\n'+body+'\nM02*').objects,.001,stats())

class GeometryTests(unittest.TestCase):
    def test_object_observer_preserves_polarity_and_image(self):
        from shapely import to_wkb
        file=GerberFile.from_string('%FSLAX35Y35*%\n%MOIN*%\n%ADD10C,0.020*%\n%ADD11C,0.010*%\nD10*\nX0Y0D03*\n%LPC*%\nD11*\nX0Y0D03*\n%LPD*%\nX0Y0D03*\nM02*')
        seen=[]
        a=compose_objects(file.objects,.001,stats())
        b=compose_objects(file.objects,.001,stats(),object_sink=lambda i,o,p,g,d:seen.append((i,d,len(p))))
        self.assertEqual(to_wkb(a),to_wkb(b));self.assertEqual(seen,[(0,True,1),(1,False,1),(2,True,1)])
    def test_tiled_raw_difference_matches_global_across_tile_edges(self):
        from shapely.geometry import box
        a=box(0,0,30,30).difference(box(5,5,15,15)).union(Point(40,10).buffer(5))
        b=box(.03,0,30.03,30).difference(box(5,5,15,15)).union(Point(40,10).buffer(4))
        d,s,tiles=tiled_compare(a,b,.01,10)
        self.assertLess(d.symmetric_difference(a.symmetric_difference(b)).area,1e-8)
        self.assertGreater(s.area,1)
        self.assertAlmostEqual(d.area,sum(t['raw_area_mil2'] for t in tiles),places=8)
    def test_tiled_equal_is_empty_including_edges(self):
        a=Point(0,0).buffer(20)
        d,s,_=tiled_compare(a,a,.01,10)
        self.assertTrue(d.is_empty);self.assertTrue(s.is_empty)
    def test_circle_area_and_sagitta(self):
        g=primitive_geometry(gp.Circle(0,0,.01),.001,stats())
        self.assertLessEqual(10-Point(0,0).distance(g.boundary),.001000001)
        self.assertLessEqual(math.pi*100-g.area,math.pi*(10**2-(10-.001)**2))
    def test_cw_and_ccw_arc(self):
        a=arc_points((10,0),(0,10),(0,0),False,.001,stats());b=arc_points((10,0),(0,10),(0,0),True,.001,stats())
        self.assertGreater(len(b),len(a)*2);self.assertTrue(all(x>=-1e-9 and y>=-1e-9 for x,y in a));self.assertTrue(any(y<0 for x,y in b))
    def test_full_arc_is_not_empty(self):
        p=gp.Arc(.01,0,.01,0,0,0,False,.002);g=primitive_geometry(p,.001,stats())
        self.assertAlmostEqual(g.area,math.pi*(11**2-9**2),delta=.2);self.assertFalse(g.covers(Point(0,0)))
    def test_rotated_rectangle_is_not_aabb(self):
        g=primitive_geometry(gp.Rectangle(0,0,.02,.01,math.pi/4),.001,stats())
        self.assertAlmostEqual(g.area,200);self.assertFalse(g.covers(Point(g.bounds[0]+.1,g.bounds[1]+.1)))
    def test_zero_length_line_is_disk(self):
        g=primitive_geometry(gp.Line(0,0,0,0,.02),.001,stats())
        self.assertTrue(g.equals_exact(primitive_geometry(gp.Circle(0,0,.01),.001,stats()),0))
    def test_cut_in_hole(self):
        ps=[(0,0),(.02,0),(.02,.02),(0,.02),(0,0),(.005,.005),(.005,.015),(.015,.015),(.015,.005),(.005,.005),(0,0)]
        g=primitive_geometry(gp.ArcPoly(ps),.001,stats());self.assertAlmostEqual(g.area,300);self.assertFalse(g.covers(Point(10,10)))
    def test_self_crossing_is_rejected(self):
        with self.assertRaises(ValueError):primitive_geometry(gp.ArcPoly([(0,0),(.01,.01),(0,.01),(.01,0)]),.001,stats())
    def test_explicit_self_crossing_diagnostic_keeps_source_error(self):
        s=stats();g=primitive_geometry(gp.ArcPoly([(0,0),(.01,.01),(0,.01),(.01,0)]),.001,s,interpret_invalid=True)
        self.assertGreater(g.area,0);self.assertEqual(s['invalid_outline_interpretations'][0]['status'],'SOURCE_GEOMETRY_ERROR_DIAGNOSTIC_ONLY')
        self.assertEqual(s['invalid_outline_interpretations'][0]['fill_rule_disagreement_area_mil2'],0)
    def test_dark_clear_order(self):
        g=image('D10*\nX0Y0D03*\n%LPC*%\nD11*\nX0Y0D03*')
        self.assertFalse(g.covers(Point(0,0)));self.assertAlmostEqual(g.area,math.pi*75,delta=.06)
        restored=image('D10*\nX0Y0D03*\n%LPC*%\nD11*\nX0Y0D03*\n%LPD*%\nX0Y0D03*')
        self.assertTrue(restored.covers(Point(0,0)))
    def test_aperture_hole_does_not_erase_existing_copper(self):
        g=image('D10*\nX0Y0D03*\nD11*\nX0Y0D03*','%ADD10C,0.006*%\n%ADD11C,0.020X0.010*%')
        self.assertTrue(g.covers(Point(0,0)));self.assertFalse(g.covers(Point(4,0)))
    def test_missing_translated_object_detected(self):
        root=Path(__file__).resolve().parents[1];a,_=render(root/'control_a.art',.005);b,_=render(root/'control_b.art',.005)
        self.assertEqual(a.symmetric_difference(a).area,0);self.assertGreater(a.symmetric_difference(b).area,100)
    def test_radial_inconsistency_is_retained(self):
        s=stats();a=arc_points((10,0),(0,10.02),(0,0),False,.001,s)
        self.assertEqual(a[-1],(0,10.02));self.assertAlmostEqual(s['max_arc_radial_inconsistency_mil'],.02)
    def test_unqualified_warning_is_not_success(self):
        with self.assertRaises(ValueError):warning_role('SyntaxWarning','Ignored unknown rotation')
    def test_legacy_modal_operation_same_geometry(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            a=image('D10*\nX0Y0D02*\nX1000Y0D01*\nX1000Y1000*')
            b=image('D10*\nX0Y0D02*\nX1000Y0D01*\nX1000Y1000D01*')
        self.assertTrue(a.equals_exact(b,0))
    def test_missing_arc_offset_is_zero_in_legacy_input(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            a=image('G75*\nD11*\nX1000Y0D02*\nG03X0Y1000I-1000D01*')
            b=image('G75*\nD11*\nX1000Y0D02*\nG03X0Y1000I-1000J0D01*')
        self.assertTrue(a.equals_exact(b,0))

if __name__=='__main__':unittest.main()
