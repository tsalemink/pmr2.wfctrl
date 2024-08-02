import logging
from os.path import join, isdir
import sys
from io import BytesIO

import urllib3

if sys.version_info > (3, 0):  # pragma: no cover
    from configparser import ConfigParser
else:  # pragma: no cover
    from ConfigParser import ConfigParser

from pmr2.wfctrl.core import BaseDvcsCmdBin, register_cmd, BaseDvcsCmd

try:
    from dulwich import porcelain
    from dulwich.errors import NotGitRepository
except ImportError:  # pragma: no cover
    dulwich_available = False

logger = logging.getLogger(__name__)


class DemoDvcsCmd(BaseDvcsCmdBin):
    binary = 'vcs'
    marker = '.marker'
    default_remote = '__default_remote__'
    _default_target = 'http://vcs.example.com/repo'

    def __init__(self, remote=None, queue=None):
        self.remote = remote
        self.queue = queue or []

    def clone(self, workspace, **kw):
        self.queue.append([self.binary, 'clone', self.remote,
                           workspace.working_dir])

    def init_new(self, workspace, **kw):
        self.queue.append([self.binary, 'init', workspace.working_dir])

    def add(self, workspace, path, **kw):
        self.queue.append([self.binary, 'add', path])

    def commit(self, workspace, message, **kw):
        self.queue.append([self.binary, 'commit', '-m', message])

    def update_remote(self, workspace, target_remote=None, **kw):
        pass

    def read_remote(self, workspace, target_remote=None, **kw):
        return self.remote or self._default_target

    def pull(self, workspace, **kw):
        self.queue.append([self.binary, 'pull'])

    def push(self, workspace, **kw):
        self.queue.append([self.binary, 'push'])


class MercurialDvcsCmd(BaseDvcsCmdBin):
    cmd_binary = 'hg'
    name = 'mercurial'
    marker = '.hg'
    default_remote = 'default'
    _hgrc = 'hgrc'
    _committer = None

    def _args(self, workspace, *args):
        result = ['-R', workspace.working_dir]
        result.extend(args)
        return result

    def set_committer(self, name, email, **kw):
        # TODO persist config.
        self._committer = '%s <%s>' % (name, email)

    def clone(self, workspace, **kw):
        return self.execute('clone', self.remote, workspace.working_dir)

    def init_new(self, workspace, **kw):
        return self.execute('init', workspace.working_dir)

    def add(self, workspace, path, **kw):
        return self.execute(*self._args(workspace, 'add', path))

    def commit(self, workspace, message, **kw):
        # XXX need to customize the user name
        cmd = ['commit', '-m', message]
        if self._committer:
            cmd.extend(['-u', self._committer])
        return self.execute(*self._args(workspace, *cmd))

    def read_remote(self, workspace, target_remote=None, **kw):
        target_remote = target_remote or self.default_remote
        target = join(workspace.working_dir, self.marker, self._hgrc)
        cp = ConfigParser()
        cp.read(target)
        if cp.has_option('paths', target_remote):
            return cp.get('paths', target_remote)

    def write_remote(self, workspace, target_remote=None, **kw):
        target_remote = target_remote or self.default_remote
        target = join(workspace.working_dir, self.marker, self._hgrc)
        cp = ConfigParser()
        cp.read(target)
        if not cp.has_section('paths'):
            cp.add_section('paths')
        cp.set('paths', target_remote, self.remote)
        with open(target, 'w') as fd:
            cp.write(fd)

    def pull(self, workspace, username=None, password=None, **kw):
        # XXX origin may be undefined
        target = self.get_remote(workspace,
                                 username=username, password=password)
        # XXX assuming repo is clean
        args = self._args(workspace, 'pull', target)
        return self.execute(*args)

    def push(self, workspace, username=None, password=None, **kw):
        # XXX origin may be undefined
        push_target = self.get_remote(workspace,
                                      username=username, password=password)
        args = self._args(workspace, 'push', push_target)
        return self.execute(*args)

    def reset_to_remote(self, workspace, branch=None):
        if branch is None:
            branch = 'tip'
        args = self._args(workspace, 'update', '-C', '-r', branch)
        return self.execute(*args)


class GitDvcsCmd(BaseDvcsCmdBin):
    cmd_binary = 'git'
    name = 'git'
    marker = '.git'

    default_remote = 'origin'
    _committer = (None, None)

    def _args(self, workspace, *args):
        worktree = workspace.working_dir
        gitdir = join(worktree, self.marker)
        result = ['--git-dir=%s' % gitdir, '--work-tree=%s' % worktree]
        result.extend(args)
        return result

    def set_committer(self, name, email, **kw):
        self._committer = (name, email)

    def clone(self, workspace, **kw):
        return self.execute('clone', self.remote, workspace.working_dir)

    def init_new(self, workspace, **kw):
        return self.execute('init', workspace.working_dir)

    def add(self, workspace, path, **kw):
        return self.execute(*self._args(workspace, 'add', path))

    def commit(self, workspace, message, **kw):
        # XXX no temporary override as far as I know.
        name, email = self._committer
        if name:
            self.execute(*self._args(workspace, 'config', 'user.name', name))
        if email:
            self.execute(*self._args(workspace, 'config', 'user.email', email))
        return self.execute(*self._args(workspace, 'commit', '-m', message))

    def read_remote(self, workspace, target_remote=None, **kw):
        target_remote = target_remote or self.default_remote
        stdout, err, return_code = self.execute(*self._args(workspace, 'remote', '-v'))
        if stdout:
            for lines in stdout.splitlines():
                remotes = lines.decode('utf8', errors='replace').split()
                if remotes[0] == target_remote:
                    # XXX assuming first one is correct
                    return remotes[1]

    def write_remote(self, workspace, target_remote=None, **kw):
        target_remote = target_remote or self.default_remote
        stdout, err, return_code = self.execute(*self._args(workspace, 'remote',
                                                            'rm', target_remote))
        stdout, err, return_code = self.execute(*self._args(workspace, 'remote',
                                                            'add', target_remote, self.remote))

    def pull(self, workspace, username=None, password=None, **kw):
        # XXX origin may be undefined
        target = self.get_remote(workspace,
                                 username=username, password=password)
        # XXX assuming repo is clean
        args = self._args(workspace, 'pull', target)
        return self.execute(*args)

    def push(self, workspace, username=None, password=None, branches=None,
             **kw):
        """
        branches
            A list of branches to push.  Defaults to --all
        """
        push_target = self.get_remote(workspace,
                                      username=username, password=password)
        args = self._args(workspace, 'push', push_target)
        if not branches:
            args.append('--all')
        elif isinstance(branches, list):  # pragma: no cover
            args.extend(branches)

        return self.execute(*args)

    def reset_to_remote(self, workspace, branch=None):
        # XXX not actually resetting to remote
        if branch is None:
            branch, _, *_ = self.execute(
                *self._args(workspace, 'branch', '--show-current'))
            branch = branch.strip()
        args = self._args(workspace, 'reset', '--hard', branch)
        return self.execute(*args)


class AuthenticatedGitDvcsCmd(GitDvcsCmd):
    name = 'authenticated_git'

    def __init__(self, remote=None, cmd_binary=None):
        super().__init__(remote=remote, cmd_binary=cmd_binary)

        self._auth_header = None

    def set_authorization(self, authorization_header):
        """
        Sets the authorization header for requests made by this class. The input should specify the type of authorization along with the
        authorization token itself (e.g., "Basic {token}").
        """
        self._auth_header = authorization_header

    def _authenticate(self, workspace):
        args = ['config', 'http.extraHeader', f'Authorization: {self._auth_header}']
        return self.execute(*self._args(workspace, *args))

    def clone(self, workspace, **kw):
        args = ['clone', '--config', f'http.extraHeader=Authorization: {self._auth_header}', self.remote, workspace.working_dir]
        return self.execute(*args)

    def pull(self, workspace, **kw):
        self._authenticate(workspace)
        target = self.read_remote(workspace)
        return self.execute(*self._args(workspace, 'pull', target))

    def push(self, workspace, **kw):
        self._authenticate(workspace)
        target = self.get_remote(workspace)
        return self.execute(*self._args(workspace, 'push', target))


class DulwichDvcsCmd(BaseDvcsCmd):
    name = 'dulwich'
    marker = '.git'

    default_remote = 'origin'
    _committer = (None, None)

    @classmethod
    def available(cls):
        try:
            from dulwich import porcelain
        except ImportError:  # pragma: no cover
            return False

        return True

    def set_committer(self, name, email, **kw):
        self._committer = (name, email)

    def clone(self, workspace, **kw):
        out_stream = BytesIO()
        err_stream = BytesIO()
        porcelain.clone(self.remote, workspace.working_dir, outstream=out_stream, errstream=err_stream)
        return out_stream.getvalue(), err_stream.getvalue(), 0

    def init_new(self, workspace, **kw):
        # Dulwich.porcelain doesn't re-initialise a repository as true git does.
        if not isdir(join(workspace.working_dir, self.marker)):
            porcelain.init(path=workspace.working_dir)

        return b'', b'', 0 if isdir(join(workspace.working_dir, self.marker)) else 1

    def add(self, workspace, path, **kw):
        rel_paths, ignored = porcelain.add(repo=workspace.working_dir, paths=[path])
        return '\n'.join(rel_paths).encode(), '\n'.join(ignored).encode(), 0

    def commit(self, workspace, message, **kw):
        output = porcelain.commit(
            repo=workspace.working_dir, message=message.encode('utf8'),
            committer=f"{self._committer[0]} <{self._committer[1]}>")
        return output, b'', 0 if output else 1

    def read_remote(self, workspace, target_remote=None, **kw):
        with porcelain.open_repo_closing(workspace.working_dir) as repo:
            _, name = porcelain.get_remote_repo(repo, target_remote)
            return name

    def write_remote(self, workspace, target_remote=None, **kw):
        target_remote = target_remote or self.default_remote
        try:
            porcelain.remote_remove(workspace.working_dir, target_remote.encode())
        except KeyError:
            pass  # assume the remote wasn't there
        porcelain.remote_add(workspace.working_dir, target_remote.encode(), self.remote.encode('utf-8'))

    def pull(self, workspace, username=None, password=None, **kw):
        out_stream = BytesIO()
        err_stream = BytesIO()
        # XXX origin may be undefined
        target = self.get_remote(workspace,
                                 username=username, password=password)
        # XXX assuming repo is clean
        try:
            result = 0
            porcelain.pull(workspace.working_dir, target.encode(), outstream=out_stream, errstream=err_stream)
        except NotGitRepository as e:
            result = 1
            err_stream.write(b'Not a Git repository ' + target.encode())

        return out_stream.getvalue(), err_stream.getvalue(), result

    def push(self, workspace, username=None, password=None, branches=None, **kw):
        outstream = BytesIO()
        errstream = BytesIO()
        push_target = self.get_remote(workspace,
                                      username=username, password=password)
        try:
            # push_target = "file://" + push_target
            porcelain.push(repo=workspace.working_dir, remote_location=push_target, refspecs=[], outstream=outstream, errstream=errstream)
            return_code = 0
        except NotGitRepository as e:
            errstream.write(b'Not a Git repository ' + push_target.encode())
            return_code = 1

        return outstream.getvalue(), errstream.getvalue(), return_code

    def reset_to_remote(self, workspace, branch=None):
        if branch is None:
            branch = porcelain.active_branch(workspace.working_dir)

        # XXX not actually resetting to remote
        porcelain.reset(workspace.working_dir, 'hard', treeish=b'HEAD')
        return b'', b'', 0


class AuthenticatedDulwichDvcsCmd(DulwichDvcsCmd):
    name = 'authenticated_dulwich'

    def __init__(self, remote=None):
        super().__init__(remote=remote)

        self._auth_header = None

    def set_authorization(self, authorization_header):
        """
        Sets the authorization header for requests made by this class. The input should specify the type of authorization along with the
        authorization token itself (e.g., "Basic {token}").
        """
        self._auth_header = authorization_header

    def _authenticate_pool_manager(self, *args, **kwargs):
        pool_manager = urllib3.PoolManager()
        pool_manager.headers['Authorization'] = self._auth_header
        return pool_manager

    def clone(self, workspace, **kw):
        pool_manager = self._authenticate_pool_manager()
        out_stream = BytesIO()
        err_stream = BytesIO()
        porcelain.clone(
            self.remote,
            workspace.working_dir,
            pool_manager=pool_manager,
            outstream=out_stream,
            errstream=err_stream
        )
        return out_stream.getvalue(), err_stream.getvalue(), 0

    def pull(self, workspace, **kw):
        pool_manager = self._authenticate_pool_manager()
        target = self.read_remote(workspace)
        out_stream = BytesIO()
        err_stream = BytesIO()
        try:
            result = 0
            porcelain.pull(
                workspace.working_dir,
                target.encode(),
                pool_manager=pool_manager,
                outstream=out_stream,
                errstream=err_stream
            )
        except NotGitRepository as e:
            result = 1
            err_stream.write(b'Not a Git repository ' + target.encode())

        return out_stream.getvalue(), err_stream.getvalue(), result

    def push(self, workspace, **kw):
        pool_manager = self._authenticate_pool_manager()
        target = self.read_remote(workspace)
        out_stream = BytesIO()
        err_stream = BytesIO()
        try:
            result = 0
            porcelain.push(
                workspace.working_dir,
                target.encode(),
                pool_manager=pool_manager,
                outstream=out_stream,
                errstream=err_stream
            )
        except NotGitRepository as e:
            result = 1
            err_stream.write(b'Not a Git repository ' + target.encode())

        return out_stream.getvalue(), err_stream.getvalue(), result


def _register():
    register_cmd(MercurialDvcsCmd, DulwichDvcsCmd, GitDvcsCmd, AuthenticatedDulwichDvcsCmd, AuthenticatedGitDvcsCmd)


register = _register
register()
del register
