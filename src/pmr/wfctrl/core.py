import os
from os.path import abspath, isabs, normpath, relpath


class WorkspaceBase(object):
    """
    Base workspace object
    """

    def __init__(self, working_dir):
        self.working_dir = abspath(normpath(working_dir))
        self.reset()

    def reset(self):
        self.files = set()

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
        # get the relative path, stripping out working dir + separator
        relname = filename[len(self.working_dir) + 1:]

        self.files.add(relname)

    def get_tracked_subpaths(self):
        return sorted(list(self.files))

    def save(self):
        raise NotImplementedError


class Workspace(WorkspaceBase):
    """
    Default workspace, file based.
    """

    def save(self):
        """
        They are already on filesystem, do nothing.
        """

        return
