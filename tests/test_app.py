#!/usr/bin/env python

from __future__ import absolute_import, unicode_literals

import os
import sys
import unittest
from io import open
from pathlib import Path

# Allow interactive execution from CLI,  cd tests; ./test_app.py
if __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from ksconf.app import get_facts_manifest_from_archive
from ksconf.app.facts import AppFacts
from ksconf.app.manifest import AppManifest
from tests.cli_helper import TestWorkDir, static_data

"""
        self._modsec01_upgrade(twd, "apps/modsecurity-add-on-for-splunk_12.tgz")
        self._modsec01_upgrade(twd, "apps/modsecurity-add-on-for-splunk_14.tgz")
        tgz = static_data("apps/modsecurity-add-on-for-splunk_11.tgz")
"""


class AppTestCase(unittest.TestCase):

    def setUp(self):
        self.twd = TestWorkDir()

    def tearDown(self):
        # Cleanup test working directory
        self.twd.clean()

    def test_AppFacts_todict(self):
        f = AppFacts("Splunk_TA_modsecurity",
                     version="1.1",
                     description="ModSecurity Add-on for Splunk.")
        f.is_configured = True
        d = f.to_dict()
        self.assertEqual(d["name"], "Splunk_TA_modsecurity")
        self.assertEqual(d["description"], "ModSecurity Add-on for Splunk.")
        self.assertEqual(d["version"], "1.1")

        td = f.to_tiny_dict("name", "build", "label")
        self.assertIs(td["build"], None)
        self.assertNotIn("check_for_updates", td)
        self.assertEqual(len(td), 6)

    def test_AppFacts_from_tarball(self):
        tarball_path = static_data("apps/modsecurity-add-on-for-splunk_11.tgz")
        app_info = AppFacts.from_archive(tarball_path)
        self.assertEqual(app_info.description, "ModSecurity Add-on for Splunk.")
        self.assertEqual(app_info.name, "Splunk_TA_modsecurity")
        self.assertEqual(app_info.version, "1.1")
        self.assertIsInstance(app_info.is_configured, bool)
        self.assertEqual(app_info.is_configured, False)

    def test_thin_manifest(self):
        tarball_path = static_data("apps/modsecurity-add-on-for-splunk_12.tgz")
        manifest = AppManifest.from_archive(tarball_path, calculate_hash=False)
        self.assertEqual(len(manifest.files), 15)
        self.assertEqual(manifest.files[0].hash, None)
        self.assertIs(manifest.hash, None)

    def test_the_do_it_all_function(self):
        tarball_path = static_data("apps/modsecurity-add-on-for-splunk_12.tgz")
        info, manifest = get_facts_manifest_from_archive(tarball_path)

        self.assertEqual(info.name, "Splunk_TA_modsecurity")
        self.assertEqual(manifest.hash, "7f9e7b63ed13befe24b12715b1e1e9202dc1186266497aad0b723fe27ca1de12")

        # No local files
        self.assertEqual(len(list(manifest.find_local())), 0)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
