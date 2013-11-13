import os
from os.path import abspath, isabs, isdir, join, normpath, relpath
import logging
from subprocess import Popen, PIPE

logger = logging.getLogger(__name__)

def dummy_action(workspace):
    return


class BaseWorkspace(object):
    """
    Base workspace object
    """

    marker = None
    files = None

    def __init__(self, working_dir, **kw):
        self.working_dir = abspath(normpath(working_dir))
        self.reset()

    def reset(self):
        self.files = set()

    def initialize(self, **kw):
        # Unused here.
        raise NotImplementedError

    def check_marker(self):
        # Unused here.
        raise NotImplementedError

    def add_file(self, filename):
        """
        Add a file.  Should be relative to the root of the working_dir.
        """

        if not isabs(filename):
            # Normalize a relative path into absolute path based inside
            # the workspace working dir.
            filename = abspath(normpath(join(self.working_dir, filename)))

        if not filename.startswith(self.working_dir):
            raise ValueError('filename not inside working dir')

        self.files.add(filename)

    def get_tracked_subpaths(self):
        return sorted(list(self.files))

    def save(self, **kw):
        raise NotImplementedError


class Workspace(BaseWorkspace):
    """
    Default workspace, file based.
    """

    def save(self, **kw):
        """
        They are already on filesystem, do nothing.
        """


class CmdWorkspace(BaseWorkspace):
    """
    Default workspace, file based.
    """

    def __init__(self, working_dir, cmd=None, **kw):
        """
        marker
            The marker path that denotes that this was already
            initialized.
        cmd_table
            A dictionary of callable objects that will be used for
            certain situations.  Keys are:

            - init
            - save
        """

        BaseWorkspace.__init__(self, working_dir)
        self.cmd = cmd
        self.update_cmd_table(cmd)
        self.initialize()

    def update_cmd_table(self, cmd):
        self.cmd_table = {}
        if cmd:
            self.cmd_table.update(cmd.cmd_table)

    def get_cmd(self, name):
        cmd = self.cmd_table.get(name)
        if not cmd:
            logger.info('%s required but no init defined', name)
            return dummy_action
        return cmd

    @property
    def marker(self):
        return self.cmd and self.cmd.marker or None

    def check_marker(self):
        if self.marker is None:
            return True
        target = join(self.working_dir, self.marker)
        logger.debug('checking isdir: %s', target)
        return isdir(target)

    def initialize(self, **kw):
        if self.check_marker():
            logger.debug('already initialized: %s', self.working_dir)
            return
        return self.get_cmd('init')(self, **kw)

    def save(self, **kw):
        """
        They are already on filesystem, do nothing.
        """

        return self.get_cmd('save')(self, **kw)


class BaseCmd(object):
    """
    Base command module

    For providing external command encapsulation.
    """

    marker = None

    def __init__(self, **kw):
        pass

    def set_committer(self, name, email, **kw):
        raise NotImplementedError

    def init(self, workspace, **kw):
        raise NotImplementedError

    def save(self, workspace, **kw):
        raise NotImplementedError

    @property
    def cmd_table(self):
        return {
            'init': self.init,
            'save': self.save,
        }


class BaseDvcsCmd(BaseCmd):
    """
    Base DVCS based command.
    """

    name = '__base__'
    cmd_binary = None

    def __init__(self, remote=None, cmd_binary=None):
        self.remote = remote
        if cmd_binary:
            self.cmd_binary = cmd_binary
        if not self._available():
            raise ValueError('the %s cmd_binary `%s` is not available' % 
                (self.name, cmd_binary))

    # class method private because this is used only with the class
    # version of the available.
    @classmethod
    def _execute(cls, args=None, cmd_binary=None):
        if not cmd_binary:
            cmd_binary = cls.cmd_binary
        if not args:
            args = []
        cmdargs = [cmd_binary]
        cmdargs.extend(args)
        p = Popen(cmdargs, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        return p.communicate()

    # public class method because this is useful before class is
    # instantiated.
    @classmethod
    def available(cls, cmd_binary=None):
        """
        Class method that reports whether the command binary is
        available.
        """

        if cmd_binary is None:
            cmd_binary = cls.cmd_binary
        if not cmd_binary:
            return False
        try:
            cls._execute(cmd_binary=cmd_binary)
        except OSError:
            return False
        return True

    # private as instance method because only startup needs this
    def _available(self):
        return self.available(cmd_binary=self.cmd_binary)

    # public instance method because instances always execute this.
    def execute(self, *args):
        """
        Executes an external command.
        """

        return self._execute(args=args, cmd_binary=self.cmd_binary)

    def init(self, workspace, **kw):
        if self.remote:
            self.clone(workspace)
        else:
            self.init_new(workspace)

    def save(self, workspace, message='', **kw):
        for path in workspace.get_tracked_subpaths():
            self.add(workspace, path)
        self.commit(workspace, message)
        self.push(workspace)

    def clone(self, workspace, **kw):
        raise NotImplementedError

    def init_new(self, workspace, **kw):
        raise NotImplementedError

    def add(self, workspace, path, **kw):
        raise NotImplementedError

    def commit(self, workspace, message, **kw):
        raise NotImplementedError

    def push(self, workspace, **kw):
        raise NotImplementedError
