#!/usr/bin/env python3
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Regression tests for copied foundations, source/test loss and preparation release gates."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("migration", Path(__file__).with_name("check-migration.py"))
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


class MigrationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = {
            "excluded_modules": ["shenyu-registry-api", "shenyu-register-client-beat", "shenyu-client-motan"],
            "source_files": [], "foundation_artifacts": ["shenyu-common"],
            "foundation_version": "2.7.2-SNAPSHOT", "client_preparation_version": "2.7.2-migration-SNAPSHOT",
        }
        self.parent = ('<artifactId>shenyu-client-java</artifactId><version>2.7.2-migration-SNAPSHOT</version>'
                       '<properties><java.version>17</java.version><shenyu.foundation.version>2.7.2-SNAPSHOT</shenyu.foundation.version>'
                       '<shenyu.migration.preparation>true</shenyu.migration.preparation><maven.deploy.skip>true</maven.deploy.skip></properties>')
        self.pom("pom.xml", self.parent)

    def write(self, path, text):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)

    def pom(self, path, text):
        self.write(path, '<project xmlns="http://maven.apache.org/POM/4.0.0">' + text + '</project>')

    def dependency(self, artifact, version):
        return (f'<dependencies><dependency><groupId>org.apache.shenyu</groupId><artifactId>{artifact}</artifactId>'
                f'<version>{version}</version></dependency></dependencies>')

    def errors(self):
        return MIGRATION.check(self.root, self.manifest)

    def test_pinned_main_foundation_dependency_is_allowed(self):
        self.pom("client/pom.xml", '<artifactId>client</artifactId>' + self.dependency("shenyu-common", "${shenyu.foundation.version}"))
        self.assertEqual([], self.errors())

    def test_foundation_must_not_use_client_version(self):
        self.pom("client/pom.xml", '<artifactId>client</artifactId>' + self.dependency("shenyu-common", "${project.version}"))
        self.assertIn("foundation shenyu-common", self.errors()[0])

    def test_client_artifacts_must_use_client_version(self):
        self.pom("client/pom.xml", '<artifactId>client</artifactId>' + self.dependency("shenyu-client-java", "${shenyu.foundation.version}"))
        self.assertIn("client dependency", self.errors()[0])

    def test_missing_imported_test_is_a_failure(self):
        self.manifest["source_files"] = [{"destination": "client/src/test/java/RetryTest.java"}]
        self.assertIn("Imported source/resource missing", self.errors()[0])

    def test_registry_and_beat_cannot_be_owned_here(self):
        for module in self.manifest["excluded_modules"]:
            self.pom(module + "/pom.xml", f'<artifactId>{module}</artifactId>')
        self.assertEqual(3, len(self.errors()))

    def test_copied_foundation_classes_are_rejected(self):
        self.write("client/src/main/java/Copied.java", "package org.apache.shenyu.register.common.dto;")
        self.assertIn("Copied main-owned", self.errors()[0])

    def test_java8_module_override_is_rejected(self):
        self.pom("client/pom.xml", '<artifactId>client</artifactId><properties><maven.compiler.source>8</maven.compiler.source></properties>')
        self.assertIn("Java 8 baseline", self.errors()[0])

    def test_missing_module_is_rejected(self):
        self.pom("pom.xml", self.parent + '<modules><module>missing</module></modules>')
        self.assertIn("missing module", self.errors()[0])

    def test_deployment_must_remain_disabled_in_preparation(self):
        self.pom("pom.xml", self.parent.replace('<maven.deploy.skip>true', '<maven.deploy.skip>false'))
        self.assertIn("maven.deploy.skip", self.errors()[0])

    def test_generated_foundation_checkout_does_not_count_as_client_source(self):
        self.pom("target/foundation-source/pom.xml", '<artifactId>shenyu-registry-api</artifactId>')
        self.assertEqual([], self.errors())


if __name__ == "__main__":
    unittest.main()
