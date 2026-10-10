import unittest
from shapely.geometry import box,GeometryCollection
from shapely import union_all
from direct_raw_job import raw_tiled

class RawTests(unittest.TestCase):
    def test_exact_self_control(self):
        g=box(-1,-1,5,6);r,t=raw_tiled(g,g,tile=2)
        self.assertTrue(r.is_empty);self.assertGreater(len(t),1)
    def test_thin_feature_survives(self):
        a=box(0,0,10,.0000001);r,t=raw_tiled(a,GeometryCollection(),tile=2)
        self.assertAlmostEqual(r.area,a.area,places=15)
    def test_tiled_and_whole_equal(self):
        a=box(-3,1,9,2);b=box(-1,-5,1,8);r,t=raw_tiled(a,b,tile=2)
        self.assertAlmostEqual(r.area,a.symmetric_difference(b).area)
        self.assertTrue(union_all(list(r.geoms)).equals(a.symmetric_difference(b)))
    def test_two_empty(self):
        r,t=raw_tiled(GeometryCollection(),GeometryCollection());self.assertTrue(r.is_empty);self.assertEqual(t,[])

if __name__=='__main__':unittest.main()
