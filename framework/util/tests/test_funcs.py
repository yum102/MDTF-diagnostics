import os
import unittest
import unittest.mock as mock # define mock os.environ so we don't mess up real env vars
from framework.util import funcs

class TestBasicClasses(unittest.TestCase):
    def test_singleton(self):
        # Can only be instantiated once
        class Temp1(funcs.Singleton):
            def __init__(self):
                self.foo = 0
        temp1 = Temp1()
        temp2 = Temp1()
        temp1.foo = 5
        self.assertEqual(temp2.foo, 5)

    def test_singleton_reset(self):
        # Verify cleanup works
        class Temp2(funcs.Singleton):
            def __init__(self):
                self.foo = 0
        temp1 = Temp2()
        temp1.foo = 5
        temp1._reset()
        temp2 = Temp2()
        self.assertEqual(temp2.foo, 0)

    def test_multimap_inverse(self):
        # test inverse map
        temp = funcs.MultiMap({'a':1, 'b':2})
        temp_inv = temp.inverse()
        self.assertIn(1, temp_inv)
        self.assertEqual(temp_inv[2], set(['b']))

    def test_multimap_setitem(self):
        # test key addition and handling of duplicate values
        temp = funcs.MultiMap({'a':1, 'b':2})
        temp['c'] = 1           
        temp_inv = temp.inverse()
        self.assertIn(1, temp_inv)
        self.assertCountEqual(temp_inv[1], set(['a','c']))
        temp['b'] = 3
        temp_inv = temp.inverse()
        self.assertNotIn(2, temp_inv)

    def test_multimap_delitem(self):
        # test item deletion
        temp = funcs.MultiMap({'a':1, 'b':2})
        del temp['b']
        temp_inv = temp.inverse()
        self.assertNotIn(2, temp_inv)

    def test_multimap_add(self):
        temp = funcs.MultiMap({'a':1, 'b':2, 'c':1})
        temp['a'].add(3)
        temp_inv = temp.inverse()
        self.assertIn(3, temp_inv)
        self.assertCountEqual(temp_inv[3], set(['a']))
        temp['a'].add(2)
        temp_inv = temp.inverse()
        self.assertIn(2, temp_inv)
        self.assertCountEqual(temp_inv[2], set(['a','b']))

    def test_multimap_add_new(self):
        temp = funcs.MultiMap({'a':1, 'b':2, 'c':1})
        temp['x'].add(2)
        temp_inv = temp.inverse()
        self.assertIn(2, temp_inv)
        self.assertCountEqual(temp_inv[2], set(['b','x']))

    def test_multimap_remove(self):
        temp = funcs.MultiMap({'a':1, 'b':2, 'c':1})
        temp['c'].add(2)
        temp['c'].remove(1)
        temp_inv = temp.inverse()
        self.assertIn(2, temp_inv)
        self.assertCountEqual(temp_inv[2], set(['b','c']))
        self.assertIn(1, temp_inv)
        self.assertCountEqual(temp_inv[1], set(['a']))

    def test_namespace_basic(self):
        test = funcs.NameSpace(name='A', B='C')
        self.assertEqual(test.name, 'A')
        self.assertEqual(test.B, 'C')
        with self.assertRaises(AttributeError):
            _ = test.D
        test.B = 'D'
        self.assertEqual(test.B, 'D')

    def test_namespace_dict_ops(self):
        test = funcs.NameSpace(name='A', B='C')
        self.assertIn('B', test)
        self.assertNotIn('D', test)

    def test_namespace_tofrom_dict(self):
        test = funcs.NameSpace(name='A', B='C')
        test2 = test.toDict()
        self.assertEqual(test2['name'], 'A')
        self.assertEqual(test2['B'], 'C')
        test3 = funcs.NameSpace.fromDict(test2)
        self.assertEqual(test3.name, 'A')
        self.assertEqual(test3.B, 'C')

    def test_namespace_copy(self):
        test = funcs.NameSpace(name='A', B='C')
        test2 = test.copy()
        self.assertEqual(test2.name, 'A')
        self.assertEqual(test2.B, 'C')
        test2.B = 'D'
        self.assertEqual(test.B, 'C')
        self.assertEqual(test2.B, 'D')

    def test_namespace_hash(self):
        test = funcs.NameSpace(name='A', B='C')
        test2 = test
        test3 = test.copy()
        test4 = test.copy()
        test4.name = 'not_the_same'
        test5 = funcs.NameSpace(name='A', B='C')
        self.assertEqual(test, test2)
        self.assertEqual(test, test3)
        self.assertNotEqual(test, test4)
        self.assertEqual(test, test5)
        set_test = set([test, test2, test3, test4, test5])
        self.assertEqual(len(set_test), 2)
        self.assertIn(test, set_test)
        self.assertIn(test4, set_test)


# ---------------------------------------------------

if __name__ == '__main__':
    unittest.main()
