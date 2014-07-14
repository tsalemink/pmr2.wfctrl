from unittest import TestCase

import os
from os.path import join
import tempfile
import shutil

from pmr2.wfctrl.core import CmdWorkspace
from pmr2.wfctrl.cmd import DemoDvcsCmd

from pmr2.wfctrl.testing.base import CoreTestCase
from pmr2.wfctrl.testing.base import CoreTests


class DemoVcsCmdWorkspaceTestCase(CoreTestCase, CoreTests):

    wks_marker = '.marker'

    def make_workspace(self):
        self.cmd = DemoDvcsCmd()
        os.mkdir(join(self.workspace_dir, self.wks_marker))
        return CmdWorkspace(self.workspace_dir, self.cmd)

    def test_cmd_new_init(self):
        self.cmd = DemoDvcsCmd()
        wks = CmdWorkspace(self.workspace_dir, self.cmd)
        self.assertEqual(self.cmd.queue, [
            ['vcs', 'init', self.workspace_dir],
        ])

    def test_cmd_new_clone(self):
        remote = 'http://example.com'
        self.cmd = DemoDvcsCmd(remote=remote)
        wks = CmdWorkspace(self.workspace_dir, self.cmd)
        self.assertEqual(self.cmd.queue, [
            ['vcs', 'clone', remote, self.workspace_dir],
        ])

        # emulate that creation, which our mocks don't do.
        os.mkdir(join(self.workspace_dir, self.wks_marker))
        self.cmd = DemoDvcsCmd(remote=remote)
        wks = CmdWorkspace(self.workspace_dir, self.cmd)
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

    def test_cmd_pull(self):
        wks = self.make_workspace()
        # TODO make a remote sync workflow of sort
        self.cmd = DemoDvcsCmd(remote='http://example.com')
        wks = CmdWorkspace(self.workspace_dir, self.cmd)
        self.cmd.pull(wks)
        self.assertEqual(self.cmd.queue, [
            ['vcs', 'pull'],
        ])

    def test_add_files_multi(self):
        CoreTests.test_add_files_multi(self)

    def test_add_files_nested(self):
        CoreTests.test_add_files_nested(self)

    def test_get_remote(self):
        wks = self.make_workspace()
        target = self.cmd.get_remote(wks)
        self.assertEqual(target, 'http://vcs.example.com/repo')
        target = self.cmd.get_remote(wks, username='u', password='p')
        self.assertEqual(target, 'http://u:p@vcs.example.com/repo')

        self.cmd._default_target = None
        target = self.cmd.get_remote(wks, username='u', password='p')
        self.assertEqual(target, '__default_remote__')
