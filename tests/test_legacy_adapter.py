import sys,unittest,warnings
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gerber_legacy_adapter import parse_legacy
from gerber_geometry import compose_objects
from gerbonara import GerberFile
from collections import Counter

HEADER='%FSLAX35Y35*%\n%MOIN*%\n%ADD10C,0.020*%\n%ADD11C,0.010*%\nD10*\n'
def parse(body):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');return parse_legacy(HEADER+body+'\nM02*')
def img(g):return compose_objects(g.objects,.005,dict(primitive_types=Counter(),zero_area_primitives=0))

class LegacyAdapterTests(unittest.TestCase):
    def test_original_g75_state_loss_reproduced(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with self.assertRaises(SyntaxError):GerberFile.from_string(HEADER+'X1000Y0D02*\nX1000Y1000D01*\nG75*\nG03X0Y2000I-1000J0*\nM02*')
    def test_g75_does_not_erase_valid_d01(self):
        a,meta=parse('X1000Y0D02*\nX1000Y1000D01*\nG75*\nG03X0Y2000I-1000J0*')
        b,_=parse('X1000Y0D02*\nX1000Y1000D01*\nG75*\nG03X0Y2000I-1000J0D01*')
        self.assertTrue(img(a).equals_exact(img(b),0));self.assertEqual(len(meta['state_adaptations']),1)
    def test_pure_g01_does_not_erase_d01(self):
        a,_=parse('X0Y0D02*X1000Y0D01*G01*X1000Y1000*');b,_=parse('X0Y0D02*X1000Y0D01*G01*X1000Y1000D01*')
        self.assertTrue(img(a).equals_exact(img(b),0))
    def test_d02_then_g75_does_not_invent_draw(self):
        with self.assertRaises(SyntaxError):parse('X1000Y0D02*G75*G03X0Y1000I-1000J0*')
    def test_d03_then_implicit_coordinates_rejected(self):
        with self.assertRaises(SyntaxError):parse('X0Y0D03*X1000Y1000*')
    def test_aperture_selection_clears_legacy_draw_mode(self):
        with self.assertRaises(SyntaxError):parse('X0Y0D02*X1000Y0D01*D11*X1000Y1000*')
    def test_explicit_d01_after_aperture_passes(self):
        g,meta=parse('X0Y0D02*X1000Y0D01*D11*X1000Y1000D01*');self.assertEqual(len(g.objects),2)
        self.assertIsNone(meta['state_adaptations'][-1]['qualified_result'])

if __name__=='__main__':unittest.main()
