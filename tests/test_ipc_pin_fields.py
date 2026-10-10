import unittest
from ipc_pin_fields import named_pin_fields

def record(reference='U1',number='AN10',flag=' '):
    return '327'+'GND'.ljust(17)+reference.ljust(6)+'-'+number.ljust(4)+flag+'     A01X+001000Y+002000'

class IpcPinFieldTests(unittest.TestCase):
    def test_four_character_pin(self):
        self.assertEqual(named_pin_fields(record())['pin'],'U1.AN10')

    def test_m_is_not_part_of_pin(self):
        result=named_pin_fields(record('C1005','1','M'))
        self.assertEqual(result['pin'],'C1005.1');self.assertEqual(result['adjacent_flag'],'M')

    def test_pin_containing_m_is_not_trimmed(self):
        self.assertEqual(named_pin_fields(record('U1','M10','M'))['pin'],'U1.M10')

    def test_unknown_adjacent_flag_rejected(self):
        with self.assertRaises(ValueError):named_pin_fields(record(flag='X'))

    def test_via_without_named_pin_rejected(self):
        with self.assertRaises(ValueError):named_pin_fields(record('VIA',''))

    def test_misplaced_separator_rejected(self):
        with self.assertRaises(ValueError):named_pin_fields(record().replace('-',' '))

if __name__=='__main__':unittest.main()
