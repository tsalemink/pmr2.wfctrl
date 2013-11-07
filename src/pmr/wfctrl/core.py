class WorkspaceBase(object):
    """
    Base workspace object
    """

    def __init__(self, working_dir):
        self.working_dir = working_dir


class Workspace(WorkspaceBase):
    """
    Default workspace, file based.
    """
