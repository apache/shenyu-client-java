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

"""Check client ownership, imported test preservation and unpublished preparation versions."""

import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

NS = {"m": "http://maven.apache.org/POM/4.0.0"}
FOUNDATION_PACKAGE = re.compile(r"^package org\.apache\.shenyu\.(?:common|registry|register\.common)\.", re.MULTILINE)


def files(root):
    for directory, children, names in os.walk(root):
        children[:] = [name for name in children if name not in {"target", ".git", "node_modules", "__pycache__"}]
        for name in names:
            yield Path(directory) / name


def check(root, manifest):
    errors = []
    paths = list(files(root))
    poms = {path: ET.parse(path) for path in paths if path.name == "pom.xml"}
    owned = {pom.findtext("m:artifactId", "", NS) for pom in poms.values()}
    for module in manifest["excluded_modules"]:
        if module in owned:
            errors.append("Forbidden module ownership: " + module)
    for source in manifest["source_files"]:
        if not (root / source["destination"]).is_file():
            errors.append("Imported source/resource missing: " + source["destination"])
    for path, pom in poms.items():
        relative = path.relative_to(root).as_posix()
        for dependency in pom.findall(".//m:dependency", NS):
            if dependency.findtext("m:groupId", "", NS) != "org.apache.shenyu":
                continue
            artifact = dependency.findtext("m:artifactId", "", NS)
            version = dependency.findtext("m:version", "", NS)
            if artifact in owned:
                if version not in {"", "${project.version}"}:
                    errors.append(f"{relative}: client dependency {artifact} must use the client reactor version")
            elif artifact not in manifest["foundation_artifacts"]:
                errors.append(f"{relative}: unreviewed main dependency {artifact}")
            elif version != "${shenyu.foundation.version}":
                errors.append(f"{relative}: foundation {artifact} must use shenyu.foundation.version")
        for module in pom.findall(".//m:modules/m:module", NS):
            if not (path.parent / module.text / "pom.xml").is_file():
                errors.append(f"{relative}: missing module {module.text}")
        for setting in ["java.version", "maven.compiler.source", "maven.compiler.target"]:
            value = pom.findtext("m:properties/m:" + setting, "", NS)
            if value in {"8", "1.8"}:
                errors.append(f"{relative}: Java 8 baseline remains in {setting}")
    parent = poms.get(root / "pom.xml")
    if parent is not None:
        properties = {
            "java.version": "17", "shenyu.foundation.version": manifest["foundation_version"],
            "shenyu.migration.preparation": "true", "maven.deploy.skip": "true",
        }
        for name, expected in properties.items():
            if parent.findtext("m:properties/m:" + name, "", NS) != expected:
                errors.append("Preparation parent property differs: " + name)
        if parent.findtext("m:version", "", NS) != manifest["client_preparation_version"]:
            errors.append("Client preparation version differs from the migration manifest")
    for path in paths:
        if path.suffix == ".java" and FOUNDATION_PACKAGE.search(path.read_text()):
            errors.append("Copied main-owned foundation class: " + path.relative_to(root).as_posix())
    return errors


if __name__ == "__main__":
    repository = Path(__file__).resolve().parents[1]
    migration = json.loads((repository / ".github/migration-source.json").read_text())
    failures = check(repository, migration)
    if failures:
        print("\n".join(failures), file=sys.stderr)
        sys.exit(1)
    print("Client ownership, pinned foundation versions and imported source/test inventory verified.")
