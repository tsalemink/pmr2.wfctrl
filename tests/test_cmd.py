from unittest import TestCase, skipIf

import os
from os.path import join, isdir, basename
import tempfile
import shutil

from pmr.wfctrl.core import CmdWorkspace
from pmr.wfctrl.cmd import GitDvcsCmd
from pmr.wfctrl.cmd import MercurialDvcsCmd

from pmr.wfctrl.testing.base import CoreTestCase
from pmr.wfctrl.testing.base import CoreTests

def fail(*a, **kw):
    raise Exception()


class RawCmdTests(object):

    marker = None
    cmdcls = None

    def test_init(self):
        self.cmd.init_new(self.workspace)
        self.assertTrue(isdir(join(self.workspace_dir, self.marker)))

    def test_clone(self):
        self.cmd.init_new(self.workspace)
        target = os.path.join(self.working_dir, 'new_target')
        # make a new workspace, currently unknown marker (vcs backend),
        # but soon to become git (see using git's cmd_table)
        workspace = CmdWorkspace(target, self.marker,
            cmd_table=self.cmd.cmd_table)
        cmd = self.cmdcls(remote=self.workspace_dir)
        cmd.clone(workspace)
        self.assertTrue(isdir(join(target, self.marker)))

    def test_clone_with_fresh_workspace(self):
        self.cmd.init_new(self.workspace)
        # XXX allow later specification of cmd_tables
        target = os.path.join(self.working_dir, 'new_target')
        cmdtable = self.cmd.cmd_table
        cmdtable['init'] = fail
        workspace = CmdWorkspace(target, self.marker,
            cmd_table=self.cmd.cmd_table)
        # new workspace got cloned.
        self.assertTrue(isdir(join(target, self.marker)))
        # XXX verify contents.

    def test_add_files(self):
        self.cmd.init_new(self.workspace)
        helper = CoreTests()
        helper.workspace_dir = self.workspace_dir
        files = helper.add_files_multi(self.workspace)
        message = 'initial commit'
        self.cmd.set_committer('Tester', 'test@example.com')
        self.workspace.save(message=message)
        self.check_commit(files, message=message,
            committer='Tester <test@example.com>')

    def check_commit(self, files, message=None, committer=None):
        raise NotImplementedError


@skipIf(not GitDvcsCmd.available(), 'git is not available')
class GitDvcsCmdTestCase(CoreTestCase, RawCmdTests):

    marker = '.git'
    cmdcls = GitDvcsCmd

    def setUp(self):
        super(GitDvcsCmdTestCase, self).setUp()
        self.cmd = GitDvcsCmd()
        self.workspace = CmdWorkspace(self.workspace_dir, self.cmd.marker,
            cmd_table=self.cmd.cmd_table)

    def check_commit(self, files, message=None, committer=None):
        stdout, stderr = GitDvcsCmd._execute(
            self.cmd._args(self.workspace, 'log'))
        self.assertTrue(message in stdout)
        self.assertTrue(committer in stdout)

        stdout, stderr = GitDvcsCmd._execute(
            self.cmd._args(self.workspace, 'ls-tree', 'master'))

        for fn in files:
            self.assertTrue(basename(fn) in stdout)


@skipIf(not MercurialDvcsCmd.available(), 'mercurial is not available')
class MercurialDvcsCmdTestCase(CoreTestCase, RawCmdTests):

    marker = '.hg'
    cmdcls = MercurialDvcsCmd

    def setUp(self):
        super(MercurialDvcsCmdTestCase, self).setUp()
        self.cmd = MercurialDvcsCmd()
        self.workspace = CmdWorkspace(self.workspace_dir, self.cmd.marker,
            cmd_table=self.cmd.cmd_table)

    def check_commit(self, files, message=None, committer=None):
        stdout, stderr = MercurialDvcsCmd._execute(
            self.cmd._args(self.workspace, 'log'))
        self.assertTrue(message in stdout)
        self.assertTrue(committer in stdout)

        stdout, stderr = MercurialDvcsCmd._execute(
            self.cmd._args(self.workspace, 'manifest'))

        for fn in files:
            self.assertTrue(basename(fn) in stdout)
