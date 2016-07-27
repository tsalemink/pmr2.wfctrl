import logging
from os.path import join, isdir
import os
import sys

if sys.version_info > (3, 0):  # pragma: no cover
    from configparser import ConfigParser
else:  # pragma: no cover
    from ConfigParser import ConfigParser

from pmr2.wfctrl.core import BaseDvcsCmdBin, register_cmd, BaseDvcsCmd
from pmr2.wfctrl.utils import set_url_cred, DecodableStringIO

try:
    from dulwich import porcelain
    # For monkey patching Dulwich
    import dulwich.porcelain
    from dulwich.errors import NotGitRepository
    from dulwich.repo import Repo
    from dulwich.client import get_transport_and_path
    from dulwich.client import HttpGitClient

    default_bytes_err_stream = getattr(sys.stderr, 'buffer', sys.stderr)
    dulwich_available = True

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
        stdout, err = self.execute(*self._args(workspace, 'remote', '-v'))
        if stdout:
            for lines in stdout.splitlines():
                remotes = lines.decode('utf8', errors='replace').split()
                if remotes[0] == target_remote:
                    # XXX assuming first one is correct
                    return remotes[1]

    def write_remote(self, workspace, target_remote=None, **kw):
        target_remote = target_remote or self.default_remote
        stdout, err = self.execute(*self._args(workspace, 'remote',
            'rm', target_remote))
        stdout, err = self.execute(*self._args(workspace, 'remote',
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
        # XXX assuming 'master' is the current branch
        if branch is None:
            branch = 'master'
        args = self._args(workspace, 'reset', '--hard', branch)
        return self.execute(*args)


def porcelain_remote(repo='.', verbose=False, outstream=sys.stdout):
    from dulwich.repo import Repo

    r = Repo(repo)
    logger.debug('porcelain.remote - {0} and '.format(repo))
    config = r.get_config()
    logger.debug('porcelain.remote - {0} and '.format(config))
    # logger.debug('porcelain.remote - {0} and '.format(config.get(('remote', 'origin'), 'url')))
    for section in config.itersections() or []:
        logger.debug('porcelain remote = {0} - {1}'.format(section[0], section[1] if len(section) > 1 else 'empty'))
        if section[0] == 'remote':
            if verbose:
                logger.debug('porcelain remote = {0}'.format(config.get(section, 'url')))
                outstream.write('{0}   {1} (fetch)\n'.format(section[1], config.get(section, 'url')))
            else:  # pragma: no cover
                outstream.write(section[1])


def porcelain_remote_rm(repo, name):
    from dulwich.repo import Repo

    delete_section = None
    r = Repo(repo)
    config = r.get_config()
    for section in config.itersections():
        if section[0] == 'remote' and len(section) > 1 and section[1] == name:
            delete_section = section

    if delete_section is not None:
        del config[delete_section]
        config.write_to_path()


def porcelain_remote_add(repo, name, url):
    from dulwich.repo import Repo

    r = Repo(repo)
    config = r.get_config()

    # Add new entries for remote
    config.set((b'remote', name.encode('utf8')), b'url', url.encode('utf8'))
    config.set(
        (b'remote', name.encode('utf8')), b'fetch',
        "+refs/heads/*:refs/remotes/{0}/*".format(name).encode('utf8'))

    # Write to disk
    config.write_to_path()


def porcelain_clone(source, target=None, bare=False, checkout=None, errstream=default_bytes_err_stream, outstream=None):
    """Clone a local or remote git repository.

    :param source: Path or URL for source repository
    :param target: Path to target repository (optional)
    :param bare: Whether or not to create a bare repository
    :param errstream: Optional stream to write progress to
    :param outstream: Optional stream to write progress to (deprecated)
    :return: The new repository
    """
    if outstream is not None:  # pragma: no cover
        import warnings
        warnings.warn("outstream= has been deprecated in favour of errstream=.", DeprecationWarning,
                stacklevel=3)
        errstream = outstream

    if checkout is None:
        checkout = (not bare)
    if checkout and bare:  # pragma: no cover
        raise ValueError("checkout and bare are incompatible")
    client, host_path = get_transport_and_path(source)

    if target is None:
        target = host_path.split("/")[-1]

    if not os.path.exists(target):
        os.mkdir(target)

    if bare:
        r = Repo.init_bare(target)
    else:
        r = Repo.init(target)
    try:
        remote_refs = client.fetch(host_path, r,
            determine_wants=r.object_store.determine_wants_all,
            progress=errstream.write)
        if checkout:
            errstream.write(b'Checking out HEAD\n')
            if b"HEAD" in remote_refs:
                r[b"HEAD"] = remote_refs[b"HEAD"]
                r.reset_index()
            else:
                errstream.write(b'Cloning empty repository?')
    except:  # pragma: no cover
        r.close()
        raise

    return r


def httpgitclient_http_request(self, url, headers={}, data=None):
    import urllib2
    import base64
    from dulwich.errors import GitProtocolError
    from urlparse import urlparse
    parsed = urlparse(url)
    if parsed.username is not None:
        url = url.replace('{0}:{1}@'.format(parsed.username, parsed.password), '')

    req = urllib2.Request(url, headers=headers, data=data)
    if parsed.username is not None:
        req.add_header('Authorization', b'Basic ' + base64.b64encode(parsed.username + b':' + parsed.password))
    try:
        resp = self.opener.open(req)
    except urllib2.HTTPError as e:
        if e.code == 404:
            raise NotGitRepository()
        if e.code != 200:  # pragma: no cover
            raise GitProtocolError("unexpected http response %d" % e.code)
    return resp


if dulwich_available:
    porcelain.remote = porcelain_remote
    porcelain.remote_rm = porcelain_remote_rm
    porcelain.remote_add = porcelain_remote_add
    porcelain.clone = porcelain_clone
    HttpGitClient._http_request = httpgitclient_http_request

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

    def write_remote(self, workspace, target_remote=None, **kw):
        pass

    def push(self, workspace, username=None, password=None, branches=None, **kw):
        outstream = DecodableStringIO()
        errstream = DecodableStringIO()
        push_target = self.get_remote(workspace,
            username=username, password=password)
        try:
            # push_target = "file://" + push_target
            porcelain.push(repo=workspace.working_dir, remote_location=push_target, refspecs=[], outstream=outstream, errstream=errstream)
        except NotGitRepository as e:
            errstream.write('Not a Git repository {0}'.format(push_target))

        return outstream.getvalue(), errstream.getvalue()

    def clone(self, workspace, **kw):
        porcelain.clone(self.remote, workspace.working_dir)

    def reset_to_remote(self, workspace, branch=None):
        outstream = DecodableStringIO()
        errstream = DecodableStringIO()
        # XXX not actually resetting to remote
        # XXX assuming 'master' is the current branch
        if branch is None:
            branch = 'master'

        porcelain.reset(workspace.working_dir, 'hard', committish=b'HEAD')
        return outstream.getvalue(), errstream.getvalue()

    def init_new(self, workspace, **kw):
        # Dulwich.porcelain doesn't re-initialise a repository as true git does.
        if not isdir(join(workspace.working_dir, self.marker)):
            porcelain.init(path=workspace.working_dir)

    def read_remote(self, workspace, target_remote=None, **kw):
        target_remote = target_remote or self.default_remote
        outstream = DecodableStringIO()
        # self.execute(*self._args(workspace, 'remote', '-v'))
        porcelain.remote(
            repo=workspace.working_dir, verbose=True, outstream=outstream)
        if outstream:
            for lines in outstream.getvalue().splitlines():
                remotes = lines.decode('utf8', errors='replace').split()
                logger.debug("remotes: {0}".format(remotes))
                if remotes[0] == target_remote:
                    # XXX assuming first one is correct
                    return remotes[1]

        logger.debug("read_remote returning None.")

    def write_remote(self, workspace, target_remote=None, **kw):
        target_remote = target_remote or self.default_remote
        porcelain.remote_rm(workspace.working_dir, target_remote)
        porcelain.remote_add(workspace.working_dir, target_remote, self.remote)

    def pull(self, workspace, username=None, password=None, **kw):
        outstream = DecodableStringIO()
        errstream = DecodableStringIO()
        # XXX origin may be undefined
        target = self.get_remote(workspace,
            username=username, password=password)
        # XXX assuming repo is clean
        try:
            porcelain.pull(workspace.working_dir, target, outstream=outstream, errstream=errstream)
        except NotGitRepository as e:
            errstream.write('Not a Git repository {0}'.format(target))

        return outstream.getvalue(), errstream.getvalue()

    def set_committer(self, name, email, **kw):
        self._committer = '%s <%s>' % (name, email)

    def commit(self, workspace, message, **kw):
        porcelain.commit(
            repo=workspace.working_dir, message=message.encode('utf8'),
            committer=self._committer.encode('utf8'))

    def add(self, workspace, path, **kw):
        if workspace.working_dir in path:
            path = path.replace(workspace.working_dir + os.sep, '')
        porcelain.add(repo=workspace.working_dir, paths=[path])


def _register():
    register_cmd(MercurialDvcsCmd, GitDvcsCmd, DulwichDvcsCmd)

register = _register
register()
del register
