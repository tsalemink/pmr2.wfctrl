from unittest import TestCase

import os
from os.path import join
import tempfile
import shutil

from pmr.wfctrl.core import Workspace

from pmr.wfctrl.testing.base import CoreTestCase
from pmr.wfctrl.testing.base import CoreTests


class FileWorkspaceTestCase(CoreTestCase, CoreTests):

    def make_workspace(self):
        return Workspace(self.workspace_dir)
