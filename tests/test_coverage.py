import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shapely.geometry import box,GeometryCollection
from geometry_coverage import directed_coverage
from geometry_tiles import tiled_compare

class CoverageTests(unittest.TestCase):
    def test_thin_missing_feature_is_not_erased(self):
        a=box(0,0,1,.00001);b=box(0,1,1,2)
        _,old,_=tiled_compare(a,b,.01,1)
        # Old erosion loses the thin part; new first direction retains it.
        self.assertEqual(old.intersection(a).area,0)
        left,right,_,_=directed_coverage(a,b,.01,1)
        self.assertAlmostEqual(left.area,a.area,places=12);self.assertGreater(right.area,0)
    def test_full_empty_side_retains_every_input(self):
        a=box(0,0,30,30);l,r,_,_=directed_coverage(a,GeometryCollection(),.01,10)
        self.assertAlmostEqual(l.area,a.area);self.assertTrue(r.is_empty)
    def test_tiling_matches_global(self):
        a=box(0,0,30,30).difference(box(3,3,18,18));b=box(.02,0,30.02,30).difference(box(5,3,20,18))
        l,r,_,radius=directed_coverage(a,b,.01,10)
        self.assertLess(l.symmetric_difference(a.difference(b.buffer(radius,quad_segs=16))).area,1e-8)
        self.assertLess(r.symmetric_difference(b.difference(a.buffer(radius,quad_segs=16))).area,1e-8)
    def test_equal(self):
        a=box(-10,-10,30,30);l,r,_,_=directed_coverage(a,a,.01,10)
        self.assertTrue(l.is_empty);self.assertTrue(r.is_empty)
    def test_translation_outside_radius_rejected(self):
        l,r,_,_=directed_coverage(box(0,0,1,1),box(.1,0,1.1,1),.01,1)
        self.assertGreater(l.area,0);self.assertGreater(r.area,0)

if __name__=='__main__':unittest.main()
