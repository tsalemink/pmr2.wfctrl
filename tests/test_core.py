from unittest import TestCase

import os
from os.path import join

from pmr2.wfctrl import core
from pmr2.wfctrl.core import BaseCmd
from pmr2.wfctrl.core import BaseDvcsCmd
from pmr2.wfctrl.core import BaseDvcsCmdBin
from pmr2.wfctrl.core import BaseWorkspace
from pmr2.wfctrl.core import Workspace
from pmr2.wfctrl.core import CmdWorkspace
from pmr2.wfctrl.cmd import DemoDvcsCmd

from pmr2.wfctrl.testing.base import CoreTestCase
from pmr2.wfctrl.testing.base import CoreTests


class CoreCmdRegistrationTestCase(TestCase):

    def setUp(self):
        self._orig_cmd, core._cmd_classes = core._cmd_classes, {}

    def tearDown(self):
        core._cmd_classes = self._orig_cmd

    def test_register_avail(self):
        class TestCmd(BaseCmd):
            marker = '.testmarker'
            name = 'test_cmd'

            @classmethod
            def available(self):
                return True
        core.register_cmd(TestCmd)
        self.assertEqual(core._cmd_classes.get('.testmarker'), TestCmd)
        self.assertEqual(core.get_cmd_by_name('test_cmd'), TestCmd)
        core.register_cmd(TestCmd)
        self.assertEqual(len(core._cmd_classes), 1)

    def test_register_unavail(self):
        class TestCmd(BaseCmd):
            marker = '.testmarker'
            @classmethod
            def available(self):
                return False
        core.register_cmd(TestCmd)
        self.assertEqual(len(core._cmd_classes), 0)


class BaseCmdTestCase(TestCase):

    def test_base_cmd(self):
        workspace = None
        cmd = BaseCmd()
        cmd_table = cmd.cmd_table
        self.assertEqual(sorted(cmd.cmd_table.keys()), ['init', 'save'])
        self.assertNotEqual(id(cmd_table), id(cmd.cmd_table))
        self.assertEqual(cmd.cmd_table['init'], cmd.init)
        self.assertEqual(cmd.cmd_table['save'], cmd.save)
        self.assertRaises(NotImplementedError, cmd.init, workspace)
        self.assertRaises(NotImplementedError, cmd.save, workspace)
        self.assertRaises(NotImplementedError, cmd.set_committer, '', '')


class BaseDvcsCmdTestCase(TestCase):

    def test_base_dvcs_cmd(self):
        cmd = BaseDvcsCmd()
        self.assertRaises(NotImplementedError, BaseDvcsCmd.available)
        self.assertRaises(NotImplementedError, cmd.execute)


class BaseDvcsCmdBinTestCase(TestCase):

    def test_dvcs_cmd_binary(self):
        self.assertFalse(BaseDvcsCmdBin.available())
        self.assertRaises(ValueError, BaseDvcsCmdBin)
        self.assertRaises(ValueError, BaseDvcsCmdBin, cmd_binary='__bad_cmd')
        # assuming this command is available on all systems.
        self.assertTrue(BaseDvcsCmdBin.available('python'))
        self.assertFalse(BaseDvcsCmdBin.available('__bad_cmd_'))

        # Pretend we have a binary here too
        vcs = BaseDvcsCmdBin(cmd_binary='python')
        self.assertTrue(isinstance(vcs, BaseDvcsCmdBin))
        # (stdout, stderr, return_code)
        self.assertEqual(len(vcs.execute()), 3)

    def test_dvcs_default_fails(self):
        cmd = BaseDvcsCmdBin(cmd_binary='python')
        workspace = None
        self.assertRaises(NotImplementedError, cmd.clone, workspace)
        self.assertRaises(NotImplementedError, cmd.init_new, workspace)
        self.assertRaises(NotImplementedError, cmd.add, workspace, '')
        self.assertRaises(NotImplementedError, cmd.commit, workspace, '')
        self.assertRaises(NotImplementedError, cmd.read_remote, workspace)
        self.assertRaises(NotImplementedError, cmd.write_remote, workspace)
        self.assertRaises(NotImplementedError, cmd.pull, workspace)
        self.assertRaises(NotImplementedError, cmd.push, workspace)
        self.assertRaises(NotImplementedError, cmd.reset_to_remote, workspace)


class BaseWorkspaceTestCase(TestCase):

    def setUp(self):
        self.workspace = BaseWorkspace('path')

    def test_failures(self):
        self.assertRaises(NotImplementedError, self.workspace.initialize)
        self.assertRaises(NotImplementedError, self.workspace.check_marker)
        self.assertRaises(NotImplementedError, self.workspace.save)


class FileWorkspaceTestCase(CoreTestCase, CoreTests):

    def make_workspace(self):
        return Workspace(self.workspace_dir)


class _DummyCmd(object):
    marker = '.marker'

    def __init__(self):
        self.result = []

    def init(self, *a, **kw):
        self.result.append('init')

    @property
    def cmd_table(self):
        return {'init': self.init}


class BareCmdWorkspaceTestCase(CoreTestCase, CoreTests):

    def make_workspace(self):
        os.mkdir(join(self.workspace_dir, _DummyCmd.marker))
        return CmdWorkspace(self.workspace_dir)

    def test_cmd_workspace(self):
        cmd = _DummyCmd()
        wks = CmdWorkspace(self.workspace_dir, cmd)
        self.assertEqual(cmd.result, ['init'])

    def test_cmd_workspace_already_inited(self):
        cmd = _DummyCmd()
        os.mkdir(join(self.workspace_dir, _DummyCmd.marker))
        wks = CmdWorkspace(self.workspace_dir, cmd)
        self.assertEqual(cmd.result, [])

    def test_cmd_workspace_no_marker_no_init(self):
        cmd = _DummyCmd()
        cmd.marker = None
        wks = CmdWorkspace(self.workspace_dir, cmd)
        self.assertEqual(cmd.result, [])

    def test_cmd_workspace_no_marker_auto(self):
        wks = CmdWorkspace(self.workspace_dir, auto=True)
        self.assertTrue(wks.cmd is None)
