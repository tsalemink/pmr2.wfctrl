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

    cmdcls = None

    @property
    def marker(self):
        return self.cmdcls.marker

    def test_init(self):
        self.cmd.init_new(self.workspace)
        self.assertTrue(isdir(join(self.workspace_dir, self.marker)))

    def test_clone(self):
        self.cmd.init_new(self.workspace)
        target = os.path.join(self.working_dir, 'new_target')
        # make a new workspace, currently unknown marker (vcs backend),
        # but soon to become git (see using git's cmd_table)
        workspace = CmdWorkspace(target)
        cmd = self.cmdcls(remote=self.workspace_dir)
        cmd.clone(workspace)
        self.assertTrue(isdir(join(target, self.marker)))

    def test_clone_with_fresh_workspace(self):
        self.cmd.init_new(self.workspace)
        target = os.path.join(self.working_dir, 'new_target')
        cmd = self.cmdcls(remote=self.workspace_dir)
        cmd.init_new = fail
        workspace = CmdWorkspace(target, cmd)
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
        stdout, stderr = self._call(self._log)
        self.assertTrue(message in stdout)
        self.assertTrue(committer in stdout)
        stdout, stderr = self._call(self._ls_root)
        for fn in files:
            self.assertTrue(basename(fn) in stdout)

    def _call(self, f, a=(), kw={}, codec='latin1'):
        stdout, stderr = f(*a, **kw)
        return stdout.decode(codec), stderr.decode(codec)

    def _log(self):
        raise NotImplementedError

    def _ls_root(self):
        raise NotImplementedError


@skipIf(not GitDvcsCmd.available(), 'git is not available')
class GitDvcsCmdTestCase(CoreTestCase, RawCmdTests):

    cmdcls = GitDvcsCmd

    def setUp(self):
        super(GitDvcsCmdTestCase, self).setUp()
        self.cmd = GitDvcsCmd()
        self.workspace = CmdWorkspace(self.workspace_dir, self.cmd)

    def _log(self):
        return GitDvcsCmd._execute(self.cmd._args(self.workspace, 'log'))

    def _ls_root(self):
        return GitDvcsCmd._execute(
            self.cmd._args(self.workspace, 'ls-tree', 'master'))


@skipIf(not MercurialDvcsCmd.available(), 'mercurial is not available')
class MercurialDvcsCmdTestCase(CoreTestCase, RawCmdTests):

    cmdcls = MercurialDvcsCmd

    def setUp(self):
        super(MercurialDvcsCmdTestCase, self).setUp()
        self.cmd = MercurialDvcsCmd()
        self.workspace = CmdWorkspace(self.workspace_dir, self.cmd)

    def _log(self):
        return MercurialDvcsCmd._execute(self.cmd._args(self.workspace, 'log'))

    def _ls_root(self):
        return MercurialDvcsCmd._execute(
            self.cmd._args(self.workspace, 'manifest'))
