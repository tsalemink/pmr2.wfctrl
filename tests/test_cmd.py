from unittest import TestCase, skipIf

import os
from os.path import join, isdir, basename
import tempfile
import shutil

from pmr.wfctrl.core import CmdWorkspace
from pmr.wfctrl.cmd import GitDvcsCmd

from pmr.wfctrl.testing.base import CoreTestCase
from pmr.wfctrl.testing.base import CoreTests

def fail(*a, **kw):
    raise Exception()


@skipIf(not GitDvcsCmd.available(), 'git is not available')
class GitDvcsCmdTestCase(CoreTestCase):

    def setUp(self):
        super(GitDvcsCmdTestCase, self).setUp()
        self.cmd = GitDvcsCmd()
        self.workspace = CmdWorkspace(self.workspace_dir, self.cmd.marker,
            cmd_table=self.cmd.cmd_table)

    def test_git_init(self):
        self.cmd.init_new(self.workspace)
        self.assertTrue(isdir(join(self.workspace_dir, '.git')))

    def test_git_clone(self):
        self.cmd.init_new(self.workspace)
        target = os.path.join(self.working_dir, 'new_target')
        # make a new workspace, currently unknown marker (vcs backend),
        # but soon to become git (see using git's cmd_table)
        workspace = CmdWorkspace(target, '.git', cmd_table=self.cmd.cmd_table)
        cmd = GitDvcsCmd(remote=self.workspace_dir)
        cmd.clone(workspace)
        self.assertTrue(isdir(join(target, '.git')))

    def test_git_clone_with_fresh_workspace(self):
        self.cmd.init_new(self.workspace)
        # XXX allow later specification of cmd_tables
        target = os.path.join(self.working_dir, 'new_target')
        cmdtable = self.cmd.cmd_table
        cmdtable['init'] = fail
        workspace = CmdWorkspace(target, '.git', cmd_table=self.cmd.cmd_table)
        # new workspace got cloned.
        self.assertTrue(isdir(join(target, '.git')))
        # XXX verify contents.

    def test_git_add_files(self):
        self.cmd.init_new(self.workspace)
        helper = CoreTests()
        helper.workspace_dir = self.workspace_dir
        files = helper.add_files_multi(self.workspace)
        self.workspace.save(message='initial commit')

        stdout, stderr = GitDvcsCmd._execute(
            self.cmd._args(self.workspace, 'log'))
        self.assertTrue('initial commit' in stdout)

        stdout, stderr = GitDvcsCmd._execute(
            self.cmd._args(self.workspace, 'ls-tree', 'master'))

        for fn in files:
            self.assertTrue(basename(fn) in stdout)
