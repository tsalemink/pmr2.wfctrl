from unittest import TestCase

import os
from os.path import join
import tempfile
import shutil

from pmr.wfctrl import core
from pmr.wfctrl.core import BaseCmd
from pmr.wfctrl.core import BaseDvcsCmd
from pmr.wfctrl.core import BaseWorkspace
from pmr.wfctrl.core import Workspace
from pmr.wfctrl.core import CmdWorkspace
from pmr.wfctrl.cmd import DemoDvcsCmd

from pmr.wfctrl.testing.base import CoreTestCase
from pmr.wfctrl.testing.base import CoreTests


class CoreCmdRegistrationTestCase(TestCase):

    def setUp(self):
        self._orig_cmd, core._cmd_classes = core._cmd_classes, {}

    def tearDown(self):
        core._cmd_classes = self._orig_cmd

    def test_register_avail(self):
        class TestCmd(BaseCmd):
            marker = '.testmarker'
            @classmethod
            def available(self):
                return True
        core.register_cmd(TestCmd)
        self.assertEqual(core._cmd_classes.get('.testmarker'), TestCmd)
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

    def test_dvcs_cmd_binary(self):
        self.assertFalse(BaseDvcsCmd.available())
        self.assertRaises(ValueError, BaseDvcsCmd)
        self.assertRaises(ValueError, BaseDvcsCmd, cmd_binary='__bad_cmd')
        # assuming this command is available on all systems.
        self.assertTrue(BaseDvcsCmd.available('python'))
        self.assertFalse(BaseDvcsCmd.available('__bad_cmd_'))

        # Pretend we have a binary here too
        vcs = BaseDvcsCmd(cmd_binary='python')
        self.assertTrue(isinstance(vcs, BaseDvcsCmd))
        # (stdout, stderr)
        self.assertEqual(len(vcs.execute()), 2)

    def test_dvcs_default_fails(self):
        cmd = BaseDvcsCmd(cmd_binary='python')
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
