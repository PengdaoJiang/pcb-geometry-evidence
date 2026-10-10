import math
import unittest
from shapely.geometry import Point, box
from odb_geometry import Renderer, standard_symbol, orient_symbol


def read(body, symbols='$0 r10', features=1, custom=None):
    return Renderer(.001, custom).features('UNITS=INCH\nF '+str(features)+'\n'+symbols+'\n'+body)[0]


class OdbGeometryTests(unittest.TestCase):
    def test_round_circle_area(self):
        g=read('P 1 2 0 P 0 8 0')
        self.assertAlmostEqual(g.area,math.pi*25,delta=.04)
        self.assertAlmostEqual(g.centroid.x,1000);self.assertAlmostEqual(g.centroid.y,2000)

    def test_rect_exact_area(self):
        self.assertEqual(standard_symbol('rect10x20',.001).area,200)

    def test_chamfer_four_named_corners(self):
        for c,(x,y) in zip('1234',[(4.9,9.9),(-4.9,9.9),(-4.9,-9.9),(4.9,-9.9)]):
            g=standard_symbol('rect10x20xc2x'+c,.001)
            self.assertEqual(g.area,198);self.assertFalse(g.covers(Point(x,y)))
            self.assertTrue(g.covers(Point(-x,-y)))

    def test_partial_round_correct_corner_and_limit(self):
        g=standard_symbol('rect9.47x29.92xr4.735x12',.001)
        self.assertTrue(g.is_valid)
        self.assertFalse(g.covers(Point(4.734,14.959)))
        self.assertTrue(g.covers(Point(4.734,-14.959)))
        self.assertAlmostEqual(g.area,9.47*29.92-2*4.735**2*(1-math.pi/4),delta=.03)

    def test_invalid_radius_not_repaired(self):
        with self.assertRaises(ValueError):standard_symbol('rect9.47x29.92xr5x12',.001)

    def test_oval_capsule_area(self):
        self.assertAlmostEqual(standard_symbol('oval20x10',.001).area,100+math.pi*25,delta=.04)

    def test_clockwise_then_mirror(self):
        p=box(1,2,2,3)
        self.assertEqual(tuple(round(x,10) for x in orient_symbol(p,['8','90']).bounds),(2,-2,3,-1))
        self.assertEqual(tuple(round(x,10) for x in orient_symbol(p,['9','90']).bounds),(2,1,3,2))

    def test_surface_hole(self):
        body='S P 0\nOB 0 0 I\nOS 0 .01\nOS .01 .01\nOS .01 0\nOS 0 0\nOE\nOB .002 .002 H\nOS .008 .002\nOS .008 .008\nOS .002 .008\nOS .002 .002\nOE\nSE'
        self.assertEqual(read(body).area,64)

    def test_surface_self_crossing_rejected(self):
        with self.assertRaises(ValueError):read('S P 0\nOB 0 0 I\nOS .01 .01\nOS 0 .01\nOS .01 0\nOS 0 0\nOE\nSE')

    def test_surface_unclosed_rejected(self):
        with self.assertRaises(ValueError):read('S P 0\nOB 0 0 I\nOS .01 0\nOS 0 .01\nOE\nSE')

    def test_ordered_clear_and_redraw(self):
        g=read('P 0 0 0 P 0 8 0\nP 0 0 1 N 0 8 0\nP 0 0 2 P 0 8 0','$0 s10\n$1 s6\n$2 s2',3)
        self.assertEqual(g.area,68);self.assertTrue(g.covers(Point(0,0)));self.assertFalse(g.covers(Point(2,2)))

    def test_custom_symbol_hole_does_not_clear_underlying_layer(self):
        custom={'ring':'UNITS=INCH\nF 2\n$0 s10\n$1 s6\nP 0 0 0 P 0 8 0\nP 0 0 1 N 0 8 0'}
        g=read('P 0 0 0 P 0 8 0\nP 0 0 1 P 0 8 0','$0 s2\n$1 ring',2,custom)
        self.assertEqual(g.area,68)

    def test_unsupported_resize_and_unknown_symbol_rejected(self):
        for body,symbols in [('P 0 0 -1 0 .1 P 0 8 0','$0 r10'),('P 0 0 0 P 0 8 0','$0 mystery')]:
            with self.assertRaises(ValueError):read(body,symbols)

    def test_count_mismatch_rejected(self):
        with self.assertRaises(ValueError):read('P 0 0 0 P 0 8 0',features=2)

    def test_full_circle_arc(self):
        g=read('A .1 0 .1 0 0 0 0 P 0 N')
        self.assertAlmostEqual(g.area,math.pi*(105**2-95**2),delta=1)
        self.assertFalse(g.covers(Point(0,0)))

    def test_thin_line_not_deleted(self):
        g=read('L 0 0 1 0 0 P 0','$0 r0.0001')
        self.assertGreater(g.area,.0999)

    def test_unknown_units_rejected(self):
        with self.assertRaises(ValueError):Renderer(.001).features('UNITS=MM\nF 0')

    def test_explicit_imperial_symbol_units(self):
        self.assertEqual(read('P 0 0 0 P 0 8 0','$0 rect10x20 I').area,200)
        with self.assertRaises(ValueError):read('P 0 0 0 P 0 8 0','$0 rect10x20 M')

    def test_observer_does_not_change_image(self):
        source='UNITS=INCH\nF 2\n$0 r10\nP 0 0 0 P 0 8 0\nP .02 0 0 P 0 8 0'
        seen=[]
        from shapely import to_wkb
        a,n=Renderer(.001).features(source)
        b,m=Renderer(.001,feature_sink=lambda meta,g,p:seen.append((meta['feature_index'],g.area,p))).features(source)
        self.assertEqual(n,m);self.assertEqual(to_wkb(a),to_wkb(b));self.assertEqual([v[0] for v in seen],[0,1])


if __name__=='__main__':unittest.main()
