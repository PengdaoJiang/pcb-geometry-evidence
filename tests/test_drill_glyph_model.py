import math,unittest
from drill_glyph_model import fit_uniform,outline_anchor

class GlyphModelTest(unittest.TestCase):
    def fixture(self):
        old=[dict(kind='L',a=[1,2],b=[1,4],width_mil=5),dict(kind='L',a=[1,4],b=[3,4],width_mil=5)]
        new=[dict(a=[1.004*x+.002 for x in s['a']],b=[1.004*x+.002 for x in s['b']],width_mil=5) for s in old]
        return old,new
    def test_model(self):
        a,b=self.fixture();r=fit_uniform(a,b,[0,0]);self.assertAlmostEqual(r['uniform_scale'],1.004);self.assertLess(r['max_endpoint_residual_mil'],1e-10)
    def test_reversed_stroke(self):
        a,b=self.fixture();a[0]['a'],a[0]['b']=a[0]['b'],a[0]['a'];self.assertIsNotNone(fit_uniform(a,b,[0,0]))
    def test_wrong_character_rejected(self):
        a,b=self.fixture();b[1]['b'][1]+=.2;self.assertIsNone(fit_uniform(a,b,[0,0]))
    def test_wrong_width_rejected(self):
        a,b=self.fixture();a[1]['width_mil']=4;self.assertIsNone(fit_uniform(a,b,[0,0]))
    def test_excess_scale_rejected(self):
        a,b=self.fixture()
        for r in b:
            for k in ('a','b'):r[k]=[x*2 for x in r[k]]
        self.assertIsNone(fit_uniform(a,b,[0,0]))
    def test_outline_extent_anchor(self):
        vs=[[-10,-10],[10,-10],[10,10],[-10,10]]
        src=[dict(kind='L',a=a,b=b,width_mil=5.118,feature_index=i) for i,(a,b) in enumerate(zip(vs,vs[1:]+vs[:1]))]
        sem=dict(figure='SQUARE',width_height_mil=[20,20])
        self.assertIsNotNone(outline_anchor(src,sem,[0,0]));self.assertIsNone(outline_anchor(src,sem,[1,0]))
        src[0]['a']=[-9,-10];self.assertIsNone(outline_anchor(src,sem,[0,0]))
    def test_hexagon_radius_not_rectangular_extent(self):
        vs=[[10*math.cos(math.pi/2+i*math.pi/3),10*math.sin(math.pi/2+i*math.pi/3)] for i in range(6)]
        src=[dict(kind='L',a=a,b=b,width_mil=5.118,feature_index=i) for i,(a,b) in enumerate(zip(vs,vs[1:]+vs[:1]))]
        sem=dict(figure='HEXAGON_Y',width_height_mil=[20,20])
        self.assertIsNotNone(outline_anchor(src,sem,[0,0]));self.assertIsNone(outline_anchor(src,dict(sem,figure='HEXAGON_X'),[0,0]))

if __name__=='__main__':unittest.main()
