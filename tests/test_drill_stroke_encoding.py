import unittest
from dataclasses import make_dataclass
from drill_stroke_encoding import strokes,native_semantic
Circle=make_dataclass('Circle','x y r polarity_dark'.split())
Rectangle=make_dataclass('Rectangle','x y w h rotation polarity_dark'.split())

class DrillStrokeTest(unittest.TestCase):
    def fixture(self):return [Circle(0,0,.1,True),Rectangle(.5,0,1,.2,0,True),Circle(1,0,.1,True)]
    def test_single_stroke(self):
        s,d=strokes(self.fixture());self.assertEqual(len(s),1);self.assertEqual(d,[]);self.assertEqual(s[0]['width_mil'],200)
    def test_disconnected_and_dot(self):
        s,d=strokes(self.fixture()+[Circle(3,4,.1,True)]+self.fixture());self.assertEqual((len(s),len(d)),(2,1))
    def test_wrong_cap_rejected(self):
        f=self.fixture();f[2].x+=.01
        with self.assertRaises(AssertionError):strokes(f)
    def test_negative_primitive_rejected(self):
        f=self.fixture();f[1].polarity_dark=False
        with self.assertRaises(AssertionError):strokes(f)
    def test_differing_native_semantics_rejected(self):
        a=dict(instance=dict(drill_figure_name='CROSS',drill_char='10',figure_width_height_diameter_mil=[20,20,10]))
        b=dict(instance=dict(drill_figure_name='CROSS',drill_char='12',figure_width_height_diameter_mil=[20,20,10]))
        with self.assertRaises(AssertionError):native_semantic(dict(native_hole_candidates=[a,b]),{})

if __name__=='__main__':unittest.main()
