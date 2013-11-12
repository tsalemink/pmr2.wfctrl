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

    def test_no_marker(self):
        self.assertRaises(AssertionError, CmdWorkspace, self.workspace_dir)

    def test_cmd_workspace(self):
        def init(*a, **kw):
            pass
        save = object()
        wks = CmdWorkspace(self.workspace_dir, self.wks_marker,
            cmd_table={'init': init, 'save': save})

        self.assertEqual(wks.cmd_table, {'init': init, 'save': save})


class DemoVcsCmdWorkspaceTestCase(CoreTestCase, CoreTests):

    wks_marker = '.marker'

    def make_workspace(self):
        self.cmd = DemoDvcsCmd()
        os.mkdir(join(self.workspace_dir, self.wks_marker))
        return CmdWorkspace(self.workspace_dir, self.wks_marker,
            cmd_table=self.cmd.cmd_table)

    def test_cmd_new_init(self):
        self.cmd = DemoDvcsCmd()
        wks = CmdWorkspace(self.workspace_dir, self.wks_marker,
            cmd_table=self.cmd.cmd_table)
        self.assertEqual(self.cmd.queue, [
            ['vcs', 'init', self.workspace_dir],
        ])

    def test_cmd_new_clone(self):
        remote = 'http://example.com'
        self.cmd = DemoDvcsCmd(remote=remote)
        wks = CmdWorkspace(self.workspace_dir, self.wks_marker,
            cmd_table=self.cmd.cmd_table)
        self.assertEqual(self.cmd.queue, [
            ['vcs', 'clone', remote, self.workspace_dir],
        ])

        # emulate that creation, which our mocks don't do.
        os.mkdir(join(self.workspace_dir, self.wks_marker))
        self.cmd = DemoDvcsCmd(remote=remote)
        wks = CmdWorkspace(self.workspace_dir, self.wks_marker,
            cmd_table=self.cmd.cmd_table)
        # nothing.
        self.assertEqual(self.cmd.queue, [])

    def test_cmd_add_files_simple(self):
        wks = self.make_workspace()
        # since we already have the marker, no extra command.
        # ... at least until we decide to pull.
        self.assertEqual(self.cmd.queue, [])

        filename = self.add_files_simple(wks)
        wks.save()
        self.assertEqual(self.cmd.queue, [
            ['vcs', 'add', filename],
            ['vcs', 'commit', '-m', ''],
            ['vcs', 'push'],
        ])

    def test_add_files_multi(self):
        CoreTests.test_add_files_multi(self)

    def test_add_files_nested(self):
        CoreTests.test_add_files_nested(self)
