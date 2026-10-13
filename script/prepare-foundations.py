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

"""Build pinned main-owned foundation artifacts for the unpublished migration branch."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def run(arguments, cwd):
    return subprocess.run(arguments, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()


def prepare(root, main_source=None, maven_repo=None):
    manifest = json.loads((root / ".github/migration-source.json").read_text())
    revision = manifest["main_revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("The foundation source must be pinned to a full commit SHA")
    source = main_source or root / "target/foundation-source"
    if not source.exists():
        source.mkdir(parents=True)
        run(["git", "init", "--quiet"], source)
        run(["git", "remote", "add", "origin", manifest["main_repository"]], source)
        run(["git", "fetch", "--depth=1", "origin", revision], source)
        run(["git", "checkout", "--quiet", "--detach", revision], source)
    if run(["git", "rev-parse", "HEAD"], source) != revision:
        raise ValueError("Foundation checkout does not match the pinned migration commit")
    if run(["git", "status", "--porcelain", "--untracked-files=no"], source):
        raise ValueError("Foundation checkout contains tracked changes; use a clean checkout")
    main_pom = ET.parse(source / "pom.xml")
    if main_pom.findtext("m:version", "", NS) != manifest["foundation_version"]:
        raise ValueError("Foundation version differs from the migration manifest")
    paths = run(["git", "ls-files", "--", "**/pom.xml"], source).splitlines()
    modules = {}
    for path in paths:
        artifact = ET.parse(source / path).findtext("m:artifactId", "", NS)
        modules[artifact] = str(Path(path).parent)
    selected = []
    for artifact in manifest["foundation_artifacts"]:
        if artifact.startswith(("shenyu-client-", "shenyu-register-client-", "shenyu-examples-")):
            raise ValueError("Client or example artifact is not a main-owned foundation: " + artifact)
        if artifact not in modules:
            raise ValueError("Missing foundation module: " + artifact)
        selected.append(modules[artifact])
    command = [str(source / "mvnw"), "-B", "-ntp", "-pl", ",".join(selected), "-am", "install",
               "-DskipTests", "-Dmaven.test.skip=true", "-Dmaven.javadoc.skip=true", "-Djacoco.skip=true", "-DskipRemoteResources=true"]
    if maven_repo:
        command.append("-Dmaven.repo.local=" + str(maven_repo.resolve()))
    log = root / "target/prepare-foundations.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f"Building {len(selected)} main-owned foundation modules at {revision}; log: {log}", flush=True)
    with log.open("w") as output:
        result = subprocess.run(command, cwd=source, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        print("\n".join(log.read_text().splitlines()[-50:]), flush=True)
        raise RuntimeError("Foundation build failed; inspect " + str(log))
    print("Pinned main foundations installed locally. No client artifacts or releases were published.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-source", type=Path, help="Existing clean checkout at the pinned main commit")
    parser.add_argument("--maven-repo", type=Path, help="Optional local Maven repository, also pass it to the client build")
    arguments = parser.parse_args()
    prepare(Path(__file__).resolve().parents[1], arguments.main_source, arguments.maven_repo)
