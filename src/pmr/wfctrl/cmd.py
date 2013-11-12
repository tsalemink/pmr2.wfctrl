from os.path import join

from pmr.wfctrl.core import BaseDvcsCmd


class DemoDvcsCmd(BaseDvcsCmd):

    binary = 'vcs'

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

    def push(self, workspace, **kw):
        self.queue.append([self.binary, 'push'])


class MercurialDvcsCmd(BaseDvcsCmd):

    cmd_binary = 'hg'
    name = 'mercurial'
    marker = '.hg'
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

    def push(self, workspace, branches=None, **kw):
        pass


class GitDvcsCmd(BaseDvcsCmd):

    cmd_binary = 'git'
    name = 'git'
    marker = '.git'

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

    def push(self, workspace, branches=None, **kw):
        """
        branches
            A list of branches to push.  Defaults to --all
        """
        # TODO username/password for https pushes
        # XXX origin may be undefined
        args = self._args(workspace, 'push', 'origin')
        if not branches:
            args.append('--all')
        elif isinstance(branches, list):
            args.extend(branches)

        return self.execute(*args)
