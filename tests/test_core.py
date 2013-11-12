from unittest import TestCase

import os
from os.path import join
import tempfile
import shutil

from pmr.wfctrl.core import BaseCmd
from pmr.wfctrl.core import BaseDvcsCmd
from pmr.wfctrl.core import BaseWorkspace
from pmr.wfctrl.core import Workspace
from pmr.wfctrl.core import CmdWorkspace
from pmr.wfctrl.cmd import DemoDvcsCmd

from pmr.wfctrl.testing.base import CoreTestCase
from pmr.wfctrl.testing.base import CoreTests


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


class BareCmdWorkspaceTestCase(CoreTestCase, CoreTests):

    wks_marker = '.marker'

    def make_workspace(self):
        os.mkdir(join(self.workspace_dir, self.wks_marker))
        return CmdWorkspace(self.workspace_dir, self.wks_marker)

    def test_cmd_workspace(self):
        result = []
        def init(*a, **kw):
            result.append('called')
        save = object()
        wks = CmdWorkspace(self.workspace_dir, self.wks_marker,
            cmd_table={'init': init, 'save': save})

        self.assertEqual(result, ['called'])
        self.assertEqual(wks.cmd_table, {'init': init, 'save': save})

    def test_cmd_workspace_already_inited(self):
        result = []
        def init(*a, **kw):
            result.append('called')
        os.mkdir(join(self.workspace_dir, self.wks_marker))
        wks = CmdWorkspace(self.workspace_dir, self.wks_marker,
            cmd_table={'init': init})

        self.assertEqual(result, [])

    def test_cmd_workspace_no_marker_no_init(self):
        result = []
        def init(*a, **kw):
            result.append('called')
        wks = CmdWorkspace(self.workspace_dir, None,
            cmd_table={'init': init})
        self.assertEqual(result, [])
