import os
import unittest
import mock # define mock os.environ so we don't mess up real env vars
from framework.util import processes

class TestSubprocessInteraction(unittest.TestCase):
    def test_run_shell_commands_stdout1(self):
        input = 'echo "foo"'
        out = processes.run_shell_command(input)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], 'foo')

    def test_run_shell_commands_stdout2(self):
        input = 'echo "foo" && echo "bar"'
        out = processes.run_shell_command(input)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0], 'foo')
        self.assertEqual(out[1], 'bar')
        
    def test_run_shell_commands_exitcode(self):
        input = 'echo "foo"; false'
        with self.assertRaises(Exception):
            # I couldn't get this to catch CalledProcessError specifically,
            # maybe because it takes args?
            processes.run_shell_command(input)

    def test_run_shell_commands_envvars(self):
        input = 'echo $FOO; export FOO="baz"; echo $FOO'
        out = processes.run_shell_command(input, env={'FOO':'bar'})
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0], 'bar')
        self.assertEqual(out[1], 'baz')

    @unittest.skip("Skipping poll_command tests")
    def test_poll_command_shell_true(self):
        rc = processes.poll_command('echo "foo"', shell=True)
        self.assertEqual(rc, 0)

    @unittest.skip("Skipping poll_command tests")
    def test_poll_command_shell_false(self):
        rc = processes.poll_command(['echo', 'foo'], shell=False)
        self.assertEqual(rc, 0)
    
    @unittest.skip("Skipping poll_command tests")
    def test_poll_command_error(self):
        rc = processes.poll_command(['false'], shell=False)
        self.assertEqual(rc, 1)

    def test_run_command_stdout1(self):
        out = processes.run_command(['echo', '"foo"'])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], '"foo"')

    def test_run_command_exitcode(self):
        input = ['exit', '1']
        with self.assertRaises(Exception):
            # I couldn't get this to catch CalledProcessError specifically,
            # maybe because it takes args?
            processes.run_command(input)

# ---------------------------------------------------

if __name__ == '__main__':
    unittest.main()