import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shapely.geometry import LineString
from gerbonara.graphic_primitives import Arc
from gerber_geometry import primitive_geometry
from geometry_coverage import directed_coverage

class EncodedDocumentShapeTests(unittest.TestCase):
    def test_encoded_36_chords_are_not_an_analytic_circle(self):
        r=243.75;width=5
        vertices=[(r*math.cos(i*math.pi/18),r*math.sin(i*math.pi/18)) for i in range(37)]
        polygonal=LineString(vertices).buffer(width/2,quad_segs=40)
        analytic=primitive_geometry(Arc(r/1000,0,r/1000,0,0,0,False,width/1000),.0025,{})
        left,right,_,_=directed_coverage(analytic,polygonal,.04,1000)
        self.assertGreater(left.area,100);self.assertGreater(right.area,100)
        self.assertAlmostEqual(r*(1-math.cos(math.pi/36)),.927542340137,places=9)
    def test_triangle_size_change_survives_numerical_band(self):
        a=LineString([(0,0),(39.565,79.13),(79.13,0),(0,0)]).buffer(2.56)
        b=LineString([(5.301,19.788),(39.565,79.135),(73.829,19.788),(5.301,19.788)]).buffer(2.559)
        left,right,_,_=directed_coverage(a,b,.03,100)
        self.assertGreater(left.area,100);self.assertGreater(right.area,100)

if __name__=='__main__':unittest.main()
