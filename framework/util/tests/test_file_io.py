import os
import unittest
import unittest.mock as mock # define mock os.environ so we don't mess up real env vars
from framework.util import file_io

class TestJSON(unittest.TestCase):
    def test_parse_json_basic(self):
        s = """{
            "a" : "test_string",
            "b" : 3,
            "c" : false,
            "d" : [1,2,3],
            "e" : {
                "aa" : [4,5,6],
                "bb" : true
            }
        }
        """
        d = file_io.parse_json(s)
        self.assertEqual(set(d.keys()), set(['a','b','c','d','e']))
        self.assertEqual(d['a'], "test_string")
        self.assertEqual(d['b'], 3)
        self.assertEqual(d['c'], False)
        self.assertEqual(len(d['d']), 3)
        self.assertEqual(d['d'], [1,2,3])
        self.assertEqual(set(d['e'].keys()), set(['aa','bb']))
        self.assertEqual(len(d['e']['aa']), 3)
        self.assertEqual(d['e']['aa'], [4,5,6])
        self.assertEqual(d['e']['bb'], True)

    def test_parse_json_comments(self):
        s = """
        // comment 1
        // comment 1.1 // comment 1.2 // comment 1.3

        { // comment 1.5
            // comment 2
            "a" : 1, // comment 3

            "b // c" : "// d x ////", // comment 4
            "e" : false,
            // comment 5 "quotes in a comment"
            "f": "ff" // comment 6 " unbalanced quote in a comment
        } // comment 7

        """
        d = file_io.parse_json(s)
        self.assertEqual(set(d.keys()), set(['a','b // c','e','f']))
        self.assertEqual(d['a'], 1)
        self.assertEqual(d['b // c'], "// d x ////")
        self.assertEqual(d['e'], False)
        self.assertEqual(d['f'], "ff")

    def test_write_json(self):
        pass


class TestEnvVars(unittest.TestCase):
    @mock.patch.dict('os.environ', {'TEST_OVERWRITE': 'A'})
    def test_setenv_overwrite(self):
        test_d = {'TEST_OVERWRITE': 'A'}
        file_io.setenv('TEST_OVERWRITE','B', test_d, overwrite = False)
        self.assertEqual(test_d['TEST_OVERWRITE'], 'A')
        self.assertEqual(os.environ['TEST_OVERWRITE'], 'A')

    @mock.patch.dict('os.environ', {})
    def test_setenv_str(self):
        test_d = {}
        file_io.setenv('TEST_STR','B', test_d)
        self.assertEqual(test_d['TEST_STR'], 'B')
        self.assertEqual(os.environ['TEST_STR'], 'B')

    @mock.patch.dict('os.environ', {})
    def test_setenv_int(self):
        test_d = {}        
        file_io.setenv('TEST_INT',2019, test_d)
        self.assertEqual(test_d['TEST_INT'], 2019)
        self.assertEqual(os.environ['TEST_INT'], '2019')

    @mock.patch.dict('os.environ', {})
    def test_setenv_bool(self):
        test_d = {}
        file_io.setenv('TEST_TRUE',True, test_d)
        self.assertEqual(test_d['TEST_TRUE'], True)
        self.assertEqual(os.environ['TEST_TRUE'], '1')

        file_io.setenv('TEST_FALSE',False, test_d)
        self.assertEqual(test_d['TEST_FALSE'], False)
        self.assertEqual(os.environ['TEST_FALSE'], '0')

    os_environ_check_required_envvar = {'A':'B', 'C':'D'}

    @mock.patch.dict('os.environ', os_environ_check_required_envvar)
    def test_check_required_envvar_found(self):
        # exit function normally if all variables found
        try:
            file_io.check_required_envvar('A', 'C')
        except SystemExit:
            self.fail()

    # @mock.patch.dict('os.environ', os_environ_check_required_envvar)
    # def test_check_required_envvar_not_found(self):
    #     # try to exit() if any variables not found
    #     print('\nXXXX', os.environ['A'],  os.environ['E'], '\n')
    #     self.assertRaises(SystemExit, file_io.check_required_envvar, 'A', 'E')

class TestReqDirs(unittest.TestCase):
    @mock.patch('os.path.exists', return_value = True)
    @mock.patch('os.makedirs')
    def test_check_required_dirs_found(self, mock_makedirs, mock_exists):
        # exit function normally if all directories found 
        try:
            file_io.check_required_dirs(['DIR1'], [])
            file_io.check_required_dirs([], ['DIR2'])
        except SystemExit:
            self.fail()
        mock_makedirs.assert_not_called()
 
    @mock.patch('os.path.exists', return_value = False)
    @mock.patch('os.makedirs')
    def test_check_required_dirs_not_found(self, mock_makedirs, mock_exists):
        # try to exit() if any directories not found
        self.assertRaises(OSError, file_io.check_required_dirs, ['DIR1XXX'], [])
        mock_makedirs.assert_not_called()

    @mock.patch('os.path.exists', return_value = False)
    @mock.patch('os.makedirs')
    def test_check_required_dirs_not_found_created(self, mock_makedirs, mock_exists):      
        # don't exit() and call os.makedirs if in create_if_nec          
        try:
            file_io.check_required_dirs([], ['DIR2'])
        except SystemExit:
            self.fail()
        mock_makedirs.assert_called_once_with('DIR2')


class TestBumpVersion(unittest.TestCase):
    @mock.patch('os.path.exists', return_value=False)
    def test_bump_version_noexist(self, mock_exists):
        for f in [
            'AAA', 'AAA.v1', 'D/C/B/AAA', 'D/C/B/AAAA/', 'D/C/B/AAA.v23', 
            'D/C/B/AAAA.v23/', 'A.foo', 'A.v23.foo', 'A.v23.bar.v45.foo',
            'D/C/A.foo', 'D/C/A.v23.foo', 'D/C/A.v23.bar.v45.foo'
        ]:
            f2, _ = file_io.bump_version(f)
            self.assertEqual(f, f2)

    @mock.patch('os.path.exists', return_value=False)
    def test_bump_version_getver(self, mock_exists):
        for f in [
            'AAA.v42', 'D/C/B/AAA.v42', 'D/C.v7/B/AAAA.v42/', 'A.v42.foo', 
            'A.v23.bar.v42.foo', 'D/C/A.v42.foo', 'D/C/A.v23.bar.v42.foo'
        ]:
            _, ver = file_io.bump_version(f)
            self.assertEqual(ver, 42)

    @mock.patch('os.path.exists', return_value=False)
    def test_bump_version_delver(self, mock_exists):
        for f in [
            ('AAA','AAA'), ('AAA.v1','AAA'), ('D/C/B/AA','D/C/B/AA'), 
            ('D/C.v1/B/AA/','D/C.v1/B/AA/'), ('D/C/B/AA.v23','D/C/B/AA'),
            ('D/C3/B.v8/AA.v23/','D/C3/B.v8/AA/'), ('A.foo','A.foo'), 
            ('A.v23.foo','A.foo'), ('A.v23.bar.v45.foo','A.v23.bar.foo'),
            ('D/C/A.foo','D/C/A.foo'), ('D/C.v1/A234.v3.foo','D/C.v1/A234.foo'),
            ('D/C/A.v23.bar.v45.foo','D/C/A.v23.bar.foo')
        ]:
            f1, ver = file_io.bump_version(f[0], new_v=0)
            self.assertEqual(f1, f[1])
            self.assertEqual(ver, 0)

    @mock.patch('os.path.exists', return_value=False)
    def test_bump_version_setver(self, mock_exists):
        for f in [
            ('AAA','AAA.v42'), ('AAA.v1','AAA.v42'), ('D/C/B/AA','D/C/B/AA.v42'), 
            ('D/C.v1/B/AA/','D/C.v1/B/AA.v42/'), ('D/C/B/AA.v23','D/C/B/AA.v42'),
            ('D/C3/B.v8/AA.v23/','D/C3/B.v8/AA.v42/'), ('A.foo','A.v42.foo'), 
            ('A.v23.foo','A.v42.foo'), ('A.v23.bar.v45.foo','A.v23.bar.v42.foo'),
            ('D/C/A.foo','D/C/A.v42.foo'), ('D/C.v1/A.v23.foo','D/C.v1/A.v42.foo'),
            ('D/C/A.v23.bar.v45.foo','D/C/A.v23.bar.v42.foo')
        ]:
            f1, ver = file_io.bump_version(f[0], new_v=42)
            self.assertEqual(f1, f[1])
            self.assertEqual(ver, 42)

    # following tests both get caught in an infinite loop

    # @mock.patch('os.path.exists', side_effect=itertools.cycle([True,False]))
    # def test_bump_version_dirs(self, mock_exists):
    #     for f in [
    #         ('AAA','AAA.v1',1), ('AAA.v1','AAA.v2',2), ('D/C/B/AA','D/C/B/AA.v1',1), 
    #         ('D/C.v1/B/AA/','D/C.v1/B/AA.v1/',1), ('D/C/B/AA.v23','D/C/B/AA.v24',24),
    #         ('D/C3/B.v8/AA.v9/','D/C3/B.v8/AA.v10/',10)
    #     ]:
    #         f1, ver = file_io.bump_version(f[0])
    #         self.assertEqual(f1, f[1])
    #         self.assertEqual(ver, f[2])

    # @mock.patch('os.path.exists', side_effect=itertools.cycle([True,False]))
    # def test_bump_version_files(self, mock_exists):
    #     for f in [
    #         ('A.foo','A.v1.foo',1), ('A.v23.foo','A.v24.foo',24), 
    #         ('A.v23.bar.v45.foo','A.v23.bar.v46.foo',46),
    #         ('D/C/A.foo','D/C/A.v1.foo',1), 
    #         ('D/C.v1/A.v99.foo','D/C.v1/A.v100.foo', 100),
    #         ('D/C/A.v23.bar.v78.foo','D/C/A.v23.bar.v79.foo', 79)
    #     ]:
    #         f1, ver = file_io.bump_version(f[0])
    #         self.assertEqual(f1, f[1])
    #         self.assertEqual(ver, f[2])


class TestDoubleBraceTemplate(unittest.TestCase):
    def sub(self, template_text, template_dict=dict()):
        tmp = file_io._DoubleBraceTemplate(template_text)
        return tmp.safe_substitute(template_dict)

    def test_escaped_brace_1(self):
        self.assertEqual(self.sub('{{{{'), '{{')

    def test_escaped_brace_2(self):
        self.assertEqual(self.sub("\nfoo\t bar{{{{baz\n\n"), "\nfoo\t bar{{baz\n\n")

    def test_replace_1(self):
        self.assertEqual(self.sub("{{foo}}", {'foo': 'bar'}), "bar")

    def test_replace_2(self):
        self.assertEqual(
            self.sub("asdf\t{{\t foo \n\t }}baz", {'foo': 'bar'}), 
            "asdf\tbarbaz"
            )

    def test_replace_3(self):
        self.assertEqual(
            self.sub(
                "{{FOO}}\n{{  foo }}asdf\t{{\t FOO \n\t }}baz_{{foo}}", 
                {'foo': 'bar', 'FOO':'BAR'}
            ), 
            "BAR\nbarasdf\tBARbaz_bar"
            )

    def test_replace_4(self):
        self.assertEqual(
            self.sub(
                "]{ {{_F00}}\n{{  f00 }}as{ { }\n.d'f\t{{\t _F00 \n\t }}ba} {[z_{{f00}}", 
                {'f00': 'bar', '_F00':'BAR'}
            ), 
            "]{ BAR\nbaras{ { }\n.d'f\tBARba} {[z_bar"
            )

    def test_ignore_1(self):
        self.assertEqual(self.sub("{{goo}}", {'foo': 'bar'}), "{{goo}}")

    def test_ignore_2(self):
        self.assertEqual(
            self.sub("asdf\t{{\t goo \n\t }}baz", {'foo': 'bar'}), 
            "asdf\t{{\t goo \n\t }}baz"
            )

    def test_ignore_3(self):
        self.assertEqual(
            self.sub(
                "{{FOO}}\n{{  goo }}asdf\t{{\t FOO \n\t }}baz_{{goo}}", 
                {'foo': 'bar', 'FOO':'BAR'}
            ), 
            "BAR\n{{  goo }}asdf\tBARbaz_{{goo}}"
            )

    def test_nomatch_1(self):
        self.assertEqual(self.sub("{{foo", {'foo': 'bar'}), "{{foo")

    def test_nomatch_2(self):
        self.assertEqual(
            self.sub("asdf\t{{\t foo \n\t }baz", {'foo': 'bar'}), 
            "asdf\t{{\t foo \n\t }baz"
            )

    def test_nomatch_3(self):
        self.assertEqual(
            self.sub(
                "{{FOO\n{{  foo }asdf}}\t{{\t FOO \n\t }}baz_{{foo}}", 
                {'foo': 'bar', 'FOO':'BAR'}
            ), 
            "{{FOO\n{{  foo }asdf}}\tBARbaz_bar"
            )


if __name__ == '__main__':
    unittest.main()