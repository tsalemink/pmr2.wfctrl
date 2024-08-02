import platform
from unittest import TestCase, skipIf, skip

import os
import sys
import json
import logging
from os.path import join, isdir, basename

if sys.version_info > (3, 0):  # pragma: no cover
    from io import StringIO
else:  # pragma: no cover
    from StringIO import StringIO

try:
    from dulwich import porcelain, client

except ImportError:
    pass

from pmr2.wfctrl.core import get_cmd_by_name
from pmr2.wfctrl.core import CmdWorkspace
from pmr2.wfctrl.cmd import GitDvcsCmd
from pmr2.wfctrl.cmd import MercurialDvcsCmd
from pmr2.wfctrl.cmd import DulwichDvcsCmd
from pmr2.wfctrl.cmd import AuthenticatedGitDvcsCmd
from pmr2.wfctrl.cmd import AuthenticatedDulwichDvcsCmd

from pmr2.wfctrl.testing.base import CoreTestCase
from pmr2.wfctrl.testing.base import CoreTests

logger = logging.getLogger(__name__)


def fail(*a, **kw):
    raise Exception()


class RawCmdTests(object):
    cmdcls = None
    _trap_cmds = ['push', 'pull', 'clone']

    def TrapCmd(self, *a, **kw):
        trap_cmds = self._trap_cmds

        class TrapCmd(self.cmdcls):
            def execute(self, *a, **kw):
                for t in trap_cmds:
                    if t in a:
                        return (
                            json.dumps(a).encode(),
                            json.dumps(kw).encode(),
                            0,
                        )
                return super(TrapCmd, self).execute(*a, **kw)

        return TrapCmd(*a, **kw)

    @property
    def marker(self):
        return self.cmdcls.marker

    def test_init(self):
        self.cmd.init_new(self.workspace)
        self.assertTrue(isdir(join(self.workspace_dir, self.marker)))

    def test_auto_init(self):
        self.cmd.init_new(self.workspace)
        CmdWorkspace(self.workspace_dir)
        workspace = CmdWorkspace(self.workspace_dir, auto=True)
        self.assertTrue(isinstance(workspace.cmd, self.cmdcls))

    def test_get_cmd_by_name(self):
        # generally this isn't run, it's here to make sure that the
        # first pass is run here but then the subclasses of these tests
        # HAVE to implement this check explicitly so that any accidental
        # name changes within the main class will be picked up, as it
        # can have consequences when used by users.
        self.assertEqual(get_cmd_by_name(self.cmdcls.name), self.cmdcls)
        raise NotImplementedError

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
        stdout, stderr, return_code = self._call(self._log)
        self.assertTrue(message in stdout)
        self.assertTrue(committer in stdout)
        self.assertTrue(return_code == 0)
        stdout, stderr, return_code = self._call(self._ls_root)
        for fn in files:
            self.assertTrue(basename(fn) in stdout)

    def _call(self, f, a=(), kw={}, codec='latin1'):
        stdout, stderr, return_code = f(*a, **kw)
        return stdout.decode(codec), stderr.decode(codec), return_code

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
        stdout, stderr, return_code = self._call(self._log, (new_workspace,))
        self.assertTrue('nested files' in stdout)
        self.assertTrue('single file' in stdout)
        self.assertTrue(return_code == 0)

    def test_get_remote(self):
        self.cmd.init_new(self.workspace)
        push_target = self.cmd.get_remote(self.workspace,
                                          username='username', password='password')
        # currently no errors, just the token is returned
        self.assertEqual(push_target, self.cmd.default_remote)

        self.cmd.remote = 'http://example.com/repo'
        self.cmd.write_remote(self.workspace)

        push_target = self.cmd.get_remote(self.workspace)
        self.assertEqual(push_target, 'http://example.com/repo')
        push_target = self.cmd.get_remote(self.workspace,
                                          username='username', password='password')
        self.assertEqual(push_target,
                         'http://username:password@example.com/repo')

        push_target = self.cmd.get_remote(self.workspace,
                                          target_remote='newremote',
                                          username='username', password='password')
        self.assertEqual(push_target, 'newremote')

        push_target = self.cmd.get_remote(self.workspace,
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

    def test_push_url_with_creds(self):
        workspace = CmdWorkspace(self.workspace_dir, self.cmd)
        cmd = self.TrapCmd(remote='http://example.com/')
        cmd.write_remote(workspace)
        workspace = CmdWorkspace(self.workspace_dir, cmd)
        result = cmd.push(workspace, username='username', password='password')
        self.assertTrue('http://username:password@example.com/' in result[0].decode() or
                        'http://username:password@example.com/' in result[1].decode())

    def test_pull_url_with_creds(self):
        workspace = CmdWorkspace(self.workspace_dir, self.cmd)
        cmd = self.TrapCmd(remote='http://example.com/')
        cmd.write_remote(workspace)
        workspace = CmdWorkspace(self.workspace_dir, cmd)
        result = cmd.pull(workspace, username='username', password='password')
        self.assertTrue('http://username:password@example.com/' in result[0].decode() or
                        'http://username:password@example.com/' in result[1].decode())

    def test_reset_to_remote(self):
        self.cmd.init_new(self.workspace)
        helper = CoreTests()
        helper.workspace_dir = self.workspace_dir
        self.cmd.set_committer('Tester', 'test@example.com')
        files = helper.add_files_nested(self.workspace)
        self.workspace.save(message='nested files')

        # define a remote
        remote = self._make_remote()
        self.cmd.remote = remote
        fn = helper.write_file('Test content')
        self.workspace.add_file(basename(fn))
        # make a commit, which should now push.
        self.workspace.save(message='single file')

        # write a change to the latest file

        helper.write_file('Changed content', name=fn)
        with open(fn) as fd:
            # ensure that content actually changed.
            self.assertEqual(fd.read(), 'Changed content')

        result = self.cmd.reset_to_remote(self.workspace)
        with open(fn) as fd:
            # ensure that content got resetted to the original state in
            # the remote
            c = fd.read()
            self.assertEqual(c, 'Test content')


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
        branch, _, *_ = self.cmd.execute(
            *self.cmd._args(self.workspace, 'branch', '--show-current'))
        branch = branch.strip()
        return GitDvcsCmd._execute(
            self.cmd._args(self.workspace, 'ls-tree', branch))

    def _make_remote(self):
        target = os.path.join(self.working_dir, 'remote')
        GitDvcsCmd._execute(['init', target, '--bare'])
        return target

    def test_get_cmd_by_name(self):
        self.assertEqual(get_cmd_by_name('git'), self.cmdcls)

    @skipIf(DulwichDvcsCmd.available(), 'git is not available')
    def test_auto_init(self):  # pragma: no cover
        super(GitDvcsCmdTestCase, self).test_auto_init()


@skipIf(not MercurialDvcsCmd.available(), 'mercurial is not available')
@skipIf(
    platform.python_implementation() != 'CPython',
    'only doing mercurial tests with CPython',
)
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

    def test_read_write_remote(self):
        self.cmd.init_new(self.workspace)
        cmd = MercurialDvcsCmd(remote='http://example.com/hg')
        cmd.write_remote(self.workspace)
        with open(os.path.join(self.workspace_dir, '.hg', 'hgrc')) as fd:
            self.assertTrue('default = http://example.com/hg' in fd.read())

    def test_get_cmd_by_name(self):
        self.assertEqual(get_cmd_by_name('mercurial'), self.cmdcls)


@skipIf(not DulwichDvcsCmd.available(), 'dulwich is not available')
class DulwichDvcsCmdTestCase(CoreTestCase, RawCmdTests):
    cmdcls = DulwichDvcsCmd
    _trap_cmds = []

    def setUp(self):
        super(DulwichDvcsCmdTestCase, self).setUp()
        self.cmd = DulwichDvcsCmd()
        self.workspace = CmdWorkspace(self.workspace_dir, self.cmd)

    def _make_remote(self):
        target = os.path.join(self.working_dir, 'remote')
        porcelain.init(path=target, bare=True)
        return target

    def _log(self, workspace=None):
        outstream = StringIO()
        porcelain.log(repo=self.workspace.working_dir, outstream=outstream)
        return ''.join(outstream.getvalue()).encode(), b'', 0

    def _ls_root(self, workspace=None):
        from dulwich.repo import Repo
        outstream = StringIO()
        r = Repo(self.workspace.working_dir)
        index = r.open_index()
        for blob in index.iterobjects():
            outstream.write('\t'.join(map(str, blob)) + '\n')

        return ''.join(outstream.getvalue()).encode(), b'', 0

    def test_get_cmd_by_name(self):
        self.assertEqual(get_cmd_by_name('dulwich'), self.cmdcls)

    # the following two tests mostly here for coverage purposes.
    # as they don't connect to real repositories.

    def test_push_url_with_creds(self):
        workspace = CmdWorkspace(self.workspace_dir, self.cmd)
        _, _, code = self.cmd.push(
            workspace, username='username', password='password')
        self.assertEqual(code, 1)

    def test_pull_url_with_creds(self):
        workspace = CmdWorkspace(self.workspace_dir, self.cmd)
        _, _, code = self.cmd.pull(
            workspace, username='username', password='password')
        self.assertEqual(code, 1)


@skipIf(not AuthenticatedGitDvcsCmd.available(), 'git is not available')
class AuthenticatedGitDvcsCmdTestCase(GitDvcsCmdTestCase):
    cmdcls = AuthenticatedGitDvcsCmd

    def setUp(self):
        super(AuthenticatedGitDvcsCmdTestCase, self).setUp()
        self.cmd = AuthenticatedGitDvcsCmd()
        self.workspace = CmdWorkspace(self.workspace_dir, self.cmd)

    def _log(self, workspace=None):
        return AuthenticatedGitDvcsCmd._execute(self.cmd._args(self.workspace, 'log'))

    def _ls_root(self, workspace=None):
        branch, _, *_ = self.cmd.execute(
            *self.cmd._args(self.workspace, 'branch', '--show-current'))
        branch = branch.strip()
        return AuthenticatedGitDvcsCmd._execute(
            self.cmd._args(self.workspace, 'ls-tree', branch))

    def _make_remote(self):
        target = os.path.join(self.working_dir, 'remote')
        AuthenticatedGitDvcsCmd._execute(['init', target, '--bare'])
        return target

    def test_get_cmd_by_name(self):
        self.assertEqual(get_cmd_by_name('authenticated_git'), self.cmdcls)

    def test_push_url_with_creds(self):
        credentials = 'Basic username:password'
        cmd = self.TrapCmd(remote='http://example.com/')
        cmd.set_authorization(credentials)
        workspace = CmdWorkspace(self.workspace_dir, cmd)
        cmd.push(workspace)
        auth_header = cmd.execute(*cmd._args(workspace, 'config', '--get', 'http.extraHeader'))
        self.assertEqual(f'Authorization: {credentials}', auth_header[0].decode().strip())

    def test_pull_url_with_creds(self):
        credentials = 'Basic username:password'
        cmd = self.TrapCmd(remote='http://example.com/')
        cmd.set_authorization(credentials)
        workspace = CmdWorkspace(self.workspace_dir, cmd)
        cmd.pull(workspace)
        auth_header = cmd.execute(*cmd._args(workspace, 'config', '--get', 'http.extraHeader'))
        self.assertEqual(f'Authorization: {credentials}', auth_header[0].decode().strip())

    def test_clone(self):
        credentials = 'Basic username:password'
        cmd = self.TrapCmd(remote='http://example.com/')
        cmd.set_authorization(credentials)
        target = os.path.join(self.working_dir, 'new_target')
        workspace = CmdWorkspace(target, cmd)
        cmd.init_new(workspace)
        result = cmd.clone(workspace)

        self.assertTrue(isdir(join(target, self.marker)))
        authorisation = f'http.extraHeader=Authorization: {credentials}'
        self.assertIn(authorisation, result[0].decode())

    @skip("Not applicable.")
    def test_auto_init(self):
        pass


class CustomLocalGitClient(client.LocalGitClient):
    def __init__(self, pool_manager=None, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TrapDulwichCmd(AuthenticatedDulwichDvcsCmd):
    def __init__(self,  remote=None):
        super(TrapDulwichCmd, self).__init__(remote)
        self._pool_manager = None

    def _authenticate_pool_manager(self, *args, **kwargs):
        self._pool_manager = super(TrapDulwichCmd, self)._authenticate_pool_manager(*args, **kwargs)


@skipIf(not AuthenticatedDulwichDvcsCmd.available(), 'dulwich is not available')
class AuthenticatedDulwichDvcsCmdTestCase(DulwichDvcsCmdTestCase):
    cmdcls = AuthenticatedDulwichDvcsCmd

    def setUp(self):
        super(DulwichDvcsCmdTestCase, self).setUp()
        self.cmd = AuthenticatedDulwichDvcsCmd()
        self.workspace = CmdWorkspace(self.workspace_dir, self.cmd)

        # Temporarily override the local dulwich client.
        self._default_client = client.default_local_git_client_cls
        client.default_local_git_client_cls = CustomLocalGitClient

    def tearDown(self):
        # Reset the local dulwich client.
        client.default_local_git_client_cls = self._default_client

    def test_get_cmd_by_name(self):
        self.assertEqual(get_cmd_by_name('authenticated_dulwich'), self.cmdcls)

    def test_push_url_with_creds(self):
        credentials = 'Basic username:password'
        cmd = TrapDulwichCmd()
        cmd.set_authorization(credentials)
        workspace = CmdWorkspace(self.workspace_dir, cmd)
        cmd.push(workspace)
        auth_header = cmd._pool_manager.headers['Authorization']
        self.assertEqual(credentials, auth_header)

    def test_pull_url_with_creds(self):
        credentials = 'Basic username:password'
        cmd = TrapDulwichCmd()
        cmd.set_authorization(credentials)
        workspace = CmdWorkspace(self.workspace_dir, cmd)
        cmd.pull(workspace)
        auth_header = cmd._pool_manager.headers['Authorization']
        self.assertEqual(credentials, auth_header)

    def test_clone(self):
        self.cmd.init_new(self.workspace)
        target = os.path.join(self.working_dir, 'new_target')
        workspace = CmdWorkspace(target)
        credentials = 'Basic username:password'
        cmd = TrapDulwichCmd(remote=self.workspace_dir)
        cmd.set_authorization(credentials)
        cmd.clone(workspace)

        self.assertTrue(isdir(join(target, self.marker)))
        auth_header = cmd._pool_manager.headers['Authorization']
        self.assertEqual(credentials, auth_header)

    @skip("Not applicable.")
    def test_auto_init(self):
        pass
