from unittest import TestCase

import os
import tempfile
import shutil

from pmr.wfctrl.core import Workspace


class CoreTestCase(TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    def test_create_workspace(self):
        wks = Workspace(self.working_dir)
        self.assertTrue(os.path.exists(self.working_dir))
