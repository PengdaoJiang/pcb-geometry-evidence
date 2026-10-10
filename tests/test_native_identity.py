import unittest
from native_primitive_identity_job import identity_reason,polarity_runs

class IdentityTests(unittest.TestCase):
    def test_ordered_negative_allowed(self):
        self.assertEqual(identity_reason(['pos','neg'],['pos','neg'],False),'EXACT_ORDERED_OBJECT_PRIMITIVES_EQUAL')
    def test_negative_reorder_rejected(self):
        self.assertEqual(identity_reason(['pos','neg'],['neg','pos'],False),'NEEDS_GEOMETRY_COMPARISON')
    def test_positive_reorder_allowed(self):
        self.assertEqual(identity_reason(['a','b'],['b','a'],True),'EXACT_POSITIVE_OBJECT_PRIMITIVE_MULTISET_EQUAL')
    def test_lost_duplicate_rejected(self):
        self.assertEqual(identity_reason(['a','b','b'],['a','b'],True),'NEEDS_GEOMETRY_COMPARISON')
    def test_within_negative_run_commutes(self):
        self.assertEqual(polarity_runs(['p','n1','n2','q'],[True,False,False,True]),polarity_runs(['p','n2','n1','q'],[True,False,False,True]))
    def test_cross_polarity_boundary_does_not_commute(self):
        self.assertNotEqual(polarity_runs(['p','n','q'],[True,False,True]),polarity_runs(['p','q','n'],[True,True,False]))

if __name__=='__main__':unittest.main()
