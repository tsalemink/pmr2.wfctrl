from unittest import TestCase

import os
from os.path import join
import tempfile
import shutil

from pmr.wfctrl.core import BaseWorkspace
from pmr.wfctrl.core import Workspace
from pmr.wfctrl.core import CmdWorkspace

from pmr.wfctrl.testing.base import CoreTestCase
from pmr.wfctrl.testing.base import CoreTests


class BaseWorkspaceTestCase(TestCase):

    def setUp(self):
        self.workspace = BaseWorkspace('path')

    def test_failures(self):
        self.assertRaises(NotImplementedError, self.workspace.initialize)
        self.assertRaises(NotImplementedError, self.workspace.check_marker)
        self.assertRaises(NotImplementedError, self.workspace.save)


class FileWorkspaceTestCase(CoreTestCase, CoreTests):

    def make_workspace(self):
        return Workspace(self.workspace_dir)


class BareCmdWorkspaceTestCase(CoreTestCase, CoreTests):

    wks_marker = '.marker'

    def make_workspace(self):
        os.mkdir(join(self.workspace_dir, self.wks_marker))
        return CmdWorkspace(self.workspace_dir, self.wks_marker)

    def test_no_marker(self):
        self.assertRaises(AssertionError, CmdWorkspace, self.workspace_dir)
