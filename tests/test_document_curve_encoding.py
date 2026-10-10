import math,unittest
from document_curve_encoding import association,read_strokes

class CurveAssociationTest(unittest.TestCase):
    def arc(self,**kw):
        r=dict(kind='A',a=(1,0),b=(0,1),center=(0,0),clockwise=False,width_mil=5);r.update(kw);return r

    def test_chord(self):
        r=association((1,0),(math.sqrt(.5),math.sqrt(.5)),5,self.arc(),1e-8)
        self.assertEqual(r['kind'],'ARC_CHORD');self.assertAlmostEqual(r['nominal_sagitta_mil'],1-math.cos(math.pi/8))

    def test_wrong_sector_rejected(self):
        self.assertIsNone(association((-1,0),(0,-1),5,self.arc(),1e-8))

    def test_wrong_center_rejected(self):
        self.assertIsNone(association((1,0),(0,1),5,self.arc(center=(.5,0)),1e-8))

    def test_wrong_width_rejected(self):
        self.assertIsNone(association((1,0),(0,1),4,self.arc(),1e-8))

    def test_clockwise(self):
        self.assertIsNotNone(association((1,0),(0,-1),5,self.arc(b=(0,-1),clockwise=True),1e-8))

    def test_straight_extent(self):
        s=dict(kind='L',a=(0,0),b=(1,1),width_mil=5)
        self.assertEqual(association((.2,.2),(.8,.8),5,s,1e-8)['kind'],'STRAIGHT')
        self.assertIsNone(association((.2,.2),(2,2),5,s,1e-8))

    def test_source_index_keeps_pads(self):
        x,n=read_strokes('UNITS=INCH\n$1 r5\nP 0 0 1 P 0 8 0\nL 0 0 1 1 1 P 0;ID=1')
        self.assertEqual((n,x[0]['feature_index']),(2,1))

    def test_clear_rejected(self):
        with self.assertRaises(AssertionError):read_strokes('UNITS=INCH\n$1 r5\nL 0 0 1 1 1 N 0')

if __name__=='__main__':unittest.main()
