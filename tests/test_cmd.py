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

        # of course, clone will fail.
        self.assertRaises(Exception, self.cmd.clone, self.workspace)

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

    def test_push_remote(self):
        self.cmd.init_new(self.workspace)
        helper = CoreTests()
        helper.workspace_dir = self.workspace_dir
        self.cmd.set_committer('Tester', 'test@example.com')

        files = helper.add_files_nested(self.workspace)
        self.workspace.save(message='nested files')

        # define a remote
        remote = self._make_remote()
        self.cmd.remote = remote

        # add a file, using relative path
        fn = helper.write_file('Test content')
        self.workspace.add_file(basename(fn))
        # make a commit, which should now push.
        self.workspace.save(message='single file')

        # Instantiate the remote for checking
        new_workspace = CmdWorkspace(remote, self.cmdcls())
        stdout, stderr = self._call(self._log, (new_workspace,))
        self.assertTrue('nested files' in stdout)
        self.assertTrue('single file' in stdout)

    def test_get_push_target(self):
        self.cmd.init_new(self.workspace)
        push_target = self.cmd.get_push_target(self.workspace,
            username='username', password='password')
        # currently no errors, just the token is returned
        self.assertEqual(push_target, self.cmd.default_remote)

        self.cmd.remote = 'http://example.com/repo'
        self.cmd.write_remote(self.workspace)
        push_target = self.cmd.get_push_target(self.workspace)
        self.assertEqual(push_target, 'http://example.com/repo')
        push_target = self.cmd.get_push_target(self.workspace,
            username='username', password='password')
        self.assertEqual(push_target,
            'http://username:password@example.com/repo')

        push_target = self.cmd.get_push_target(self.workspace,
            target_remote='newremote',
            username='username', password='password')
        self.assertEqual(push_target, 'newremote')

        push_target = self.cmd.get_push_target(self.workspace,
            target_remote='http://alt.example.com/repo',
            username='username', password='password')
        self.assertEqual(push_target,
            'http://username:password@alt.example.com/repo')

    def test_update_remote(self):
        self.assertTrue(self.cmd.remote is None)
        target = 'http://example.com/repo'
        self.cmd.remote = target
        self.cmd.update_remote(self.workspace)
        self.assertEqual(self.cmd.remote,
            self.cmd.read_remote(self.workspace))
        # nothing should be done here
        self.cmd.update_remote(self.workspace)

        # command not tracking any remote
        self.cmd.remote = None
        self.cmd.update_remote(self.workspace)
        # should be loaded from stored
        self.assertEqual(self.cmd.remote, target)

        # command has a defined remote
        new_target = self.cmd.remote = 'http://new.example.com/repo'
        self.cmd.update_remote(self.workspace)
        # should be set to a new one and can be loaded.
        self.assertEqual(new_target,
            self.cmd.read_remote(self.workspace))


@skipIf(not GitDvcsCmd.available(), 'git is not available')
class GitDvcsCmdTestCase(CoreTestCase, RawCmdTests):

    cmdcls = GitDvcsCmd

    def setUp(self):
        super(GitDvcsCmdTestCase, self).setUp()
        self.cmd = GitDvcsCmd()
        self.workspace = CmdWorkspace(self.workspace_dir, self.cmd)

    def _log(self, workspace=None):
        return GitDvcsCmd._execute(self.cmd._args(self.workspace, 'log'))

    def _ls_root(self, workspace=None):
        return GitDvcsCmd._execute(
            self.cmd._args(self.workspace, 'ls-tree', 'master'))

    def _make_remote(self):
        target = os.path.join(self.working_dir, 'remote')
        GitDvcsCmd._execute(['init', target, '--bare'])
        return target


@skipIf(not MercurialDvcsCmd.available(), 'mercurial is not available')
class MercurialDvcsCmdTestCase(CoreTestCase, RawCmdTests):

    cmdcls = MercurialDvcsCmd

    def setUp(self):
        super(MercurialDvcsCmdTestCase, self).setUp()
        self.cmd = MercurialDvcsCmd()
        self.workspace = CmdWorkspace(self.workspace_dir, self.cmd)

    def _log(self, workspace=None):
        return MercurialDvcsCmd._execute(self.cmd._args(self.workspace, 'log'))

    def _ls_root(self, workspace=None):
        return MercurialDvcsCmd._execute(
            self.cmd._args(self.workspace, 'manifest'))

    def _make_remote(self):
        target = os.path.join(self.working_dir, 'remote')
        MercurialDvcsCmd._execute(['init', target])
        return target
