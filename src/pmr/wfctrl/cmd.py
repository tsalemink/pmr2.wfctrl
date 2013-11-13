import logging
from os.path import join
import sys

if sys.version_info > (3, 0):
    from configparser import ConfigParser
    from io import StringIO
else:
    from ConfigParser import ConfigParser
    # io.StringIO in python2.7 is not ready for the above.
    from StringIO import StringIO

from pmr.wfctrl.core import BaseDvcsCmd

logger = logging.getLogger(__name__)


class DemoDvcsCmd(BaseDvcsCmd):

    binary = 'vcs'
    marker = '.marker'

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

    def update_remote(self, workspace):
        pass

    def push(self, workspace, **kw):
        self.queue.append([self.binary, 'push'])


class MercurialDvcsCmd(BaseDvcsCmd):

    cmd_binary = 'hg'
    name = 'mercurial'
    marker = '.hg'
    _hgrc = 'hgrc'
    _default_remote_name = 'default'
    committer = None

    def _args(self, workspace, *args):
        result = ['-R', workspace.working_dir]
        result.extend(args)
        return result

    def set_committer(self, name, email, **kw):
        # TODO persist config.
        self.committer = '%s <%s>' % (name, email)

    def clone(self, workspace, **kw):
        return self.execute('clone', self.remote, workspace.working_dir)

    def init_new(self, workspace, **kw):
        return self.execute('init', workspace.working_dir)

    def add(self, workspace, path, **kw):
        return self.execute(*self._args(workspace, 'add', path))

    def commit(self, workspace, message, **kw):
        # XXX need to customize the user name
        cmd = ['commit', '-m', message]
        if self.committer:
            cmd.extend(['-u', self.committer])
        return self.execute(*self._args(workspace, *cmd))

    def _get_current_origin(self, workspace):
        target = join(workspace.working_dir, self._hgrc)
        cp = ConfigParser()
        cp.read(target)
        if cp.has_option('paths', self._default_remote_name):
            return cp.get('paths', self._default_remote_name)

    def _write_current_origin(self, workspace):
        target = join(workspace.working_dir, self._hgrc)
        cp = ConfigParser()
        cp.read(target)
        if not cp.has_section('paths'):
            cp.add_section('paths')
        cp.set('paths', self._default_remote_name, self.remote)
        with open(target, 'w') as fd:
            cp.write(fd)

    def update_remote(self, workspace):
        stored_remote = self._get_current_origin(workspace)
        if stored_remote and self.remote:
            if self.remote == stored_remote:
                logger.debug('remotes matched, not issuing update command')
                return
            logger.debug('updating stored remote with current remote')
            self._write_current_origin(workspace)
        elif self.remote is None and stored_remote is None:
            logger.info('no default remote define, push will fail')
        elif self.remote and stored_remote is None:
            logger.info('storing the defined remote in cmd object')
            self._write_current_origin(workspace)
        elif self.remote is None and stored_remote:
            logger.debug('using stored remote')
            self.remote = stored_remote

    def push(self, workspace, **kw):
        # TODO username/password for https pushes
        # XXX origin may be undefined
        args = self._args(workspace, 'push')
        return self.execute(*args)


class GitDvcsCmd(BaseDvcsCmd):

    cmd_binary = 'git'
    name = 'git'
    marker = '.git'

    _default_remote_name = 'origin'

    def _args(self, workspace, *args):
        worktree = workspace.working_dir
        gitdir = join(worktree, self.marker)
        result = ['--git-dir=%s' % gitdir, '--work-tree=%s' % worktree]
        result.extend(args)
        return result

    def set_committer(self, name, email, **kw):
        self.committer = (name, email)

    def clone(self, workspace, **kw):
        return self.execute('clone', self.remote, workspace.working_dir)

    def init_new(self, workspace, **kw):
        return self.execute('init', workspace.working_dir)

    def add(self, workspace, path, **kw):
        return self.execute(*self._args(workspace, 'add', path))

    def commit(self, workspace, message, **kw):
        # XXX no temporary override as far as I know.
        name, email = self.committer
        self.execute(*self._args(workspace, 'config', 'user.name', name))
        self.execute(*self._args(workspace, 'config', 'user.email', email))
        return self.execute(*self._args(workspace, 'commit', '-m', message))

    def _get_current_origin(self, workspace):
        stdout, err = self.execute(*self._args(workspace, 'remote', '-v'))
        if stdout:
            for lines in stdout.splitlines():
                remotes = lines.split()
                if remotes[0] == self._default_remote_name:
                    # XXX assuming first one is correct
                    return remotes[1]

    def update_remote(self, workspace):
        default_origin = self._default_remote_name
        stored_remote = self._get_current_origin(workspace)

        if stored_remote and self.remote:
            if self.remote == stored_remote:
                logger.debug('remotes matched, not issuing update command')
                return
            logger.debug('updating stored remote with current remote')
            stdout, err = self.execute(*self._args(workspace, 'remote',
                'set-url', default_origin, self.remote))
        elif self.remote is None and stored_remote is None:
            logger.info('no default remote define, push will fail')
        elif self.remote and stored_remote is None:
            logger.info('storing the defined remote in cmd object')
            stdout, err = self.execute(*self._args(workspace, 'remote',
                'add', default_origin, self.remote))
        elif self.remote is None and stored_remote:
            logger.debug('using stored remote')
            self.remote = stored_remote

    def push(self, workspace, branches=None, **kw):
        """
        branches
            A list of branches to push.  Defaults to --all
        """
        # TODO username/password for https pushes
        # XXX origin may be undefined
        args = self._args(workspace, 'push', self._default_remote_name)
        if not branches:
            args.append('--all')
        elif isinstance(branches, list):
            args.extend(branches)

        return self.execute(*args)
