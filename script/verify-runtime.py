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

"""Run the pinned source Admin/bootstrap with the independently built HTTP example.

This is source-candidate evidence, not certification of released version pairs.
All services bind to loopback, use private ephemeral ports and are stopped on exit.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import ProxyHandler, Request, build_opener
import uuid

sys.dont_write_bytecode = True
NAMESPACE = "649330b6-c2d7-4edc-be8e-8a54df9eb385"
EXAMPLE = "shenyu-examples/shenyu-examples-http"
GRPC_EXAMPLE = "shenyu-examples/shenyu-examples-grpc"
MCP_EXAMPLE = "shenyu-examples/shenyu-examples-mcp"
EXAMPLES = ",".join((EXAMPLE, GRPC_EXAMPLE, MCP_EXAMPLE))
VERSION_HEADER = "X-Shenyu-Register-Protocol-Version"
CLIENT_HEADER = "X-Shenyu-Client-Version"
OPENER = build_opener(ProxyHandler({}))


def request(url, body=None, headers=None, method=None):
    data = None if body is None else json.dumps(body).encode()
    supplied = {"Content-Type": "application/json", **(headers or {})}
    try:
        response = OPENER.open(Request(url, data=data, headers=supplied, method=method), timeout=5)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.read().decode(), dict(response.headers)


def java_binary():
    home = os.environ.get("JAVA_HOME")
    return str(Path(home) / "bin/java") if home else "java"


def require(condition, evidence):
    if not condition:
        raise AssertionError(evidence)


def probe_result(log):
    lines = [re.sub(r"\x1b\[[0-9;]*m", "", line) for line in log.read_text().splitlines()]
    results = [line.removeprefix("PROBE_RESULT=") for line in lines if line.startswith("PROBE_RESULT=")]
    require(len(results) == 1, "Probe did not produce one evidence result: " + str(log))
    return json.loads(results[0])


def client_build_fingerprint(root):
    paths = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root).split(b"\0")
    digest = hashlib.sha256()
    for raw in sorted(set(paths)):
        path = Path(os.fsdecode(raw))
        if raw and (path.name == "pom.xml" or path.suffix == ".java" or "src/main/resources" in path.as_posix()
                    or path.as_posix() == ".github/migration-source.json"):
            digest.update(raw)
            digest.update((root / path).read_bytes())
    return digest.hexdigest()


def gateway_upstream_data(log, context):
    latest = None
    for line in log.read_text().splitlines():
        marker = line.find('{"groupType":"DISCOVER_UPSTREAM"')
        if marker < 0:
            continue
        frame, _ = json.JSONDecoder().raw_decode(line[marker:])
        for item in frame["data"]:
            if item.get("selectorName") == context and item.get("namespaceId") == NAMESPACE:
                latest = item["upstreamDataList"]
    return latest


def gateway_snapshot(log, context):
    data = gateway_upstream_data(log, context)
    return None if data is None else sorted(upstream["url"] for upstream in data)


def gateway_empty(url):
    status, body, _ = request(url)
    return status == 200 and json.loads(body).get("code") == -119


def main_owned_classpath(classpath):
    for entry in classpath.split(os.pathsep):
        name = Path(entry).name
        if name.startswith(("shenyu-client-", "shenyu-examples-", "shenyu-register-client-", "shenyu-spring-boot-starter-client-")):
            if not name.startswith(("shenyu-register-client-beat-", "shenyu-spring-boot-starter-client-beat-")):
                raise ValueError("Main runtime imports a business-client artifact: " + name)


def wait_for(label, condition, processes=(), timeout=90):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        for name, process in processes:
            if process.poll() is not None:
                raise RuntimeError(f"{name} exited with {process.returncode}; inspect its runtime log")
        try:
            result = condition()
            if result:
                print("Verified " + label, flush=True)
                return result
        except (URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as error:
            last_error = error
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {label}; last error: {last_error}")


class RecordingProxy:
    """Forward actual client requests to actual Admin; retain only contract fields."""

    def __init__(self, admin_url, port):
        self.events = []
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                path = urlsplit(self.path).path
                headers = {key: value for key, value in self.headers.items()
                           if key.lower() not in {"host", "content-length", "connection"}}
                upstream = Request(admin_url + self.path, data=raw, headers=headers, method="POST")
                try:
                    response = OPENER.open(upstream, timeout=10)
                except HTTPError as error:
                    response = error
                with response:
                    body = response.read()
                    status = response.status
                    version = response.headers.get(VERSION_HEADER)
                    self.send_response(status)
                    self.send_header("Content-Type", response.headers.get("Content-Type", "text/plain"))
                    if version:
                        self.send_header(VERSION_HEADER, version)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                # Never save login credentials, tokens or login response bodies.
                if path != "/platform/login":
                    event = {"path": path, "body": json.loads(raw), "status": status,
                             "protocol_version": self.headers.get(VERSION_HEADER),
                             "client_version": self.headers.get(CLIENT_HEADER),
                             "authenticated": bool(self.headers.get("X-Access-Token")),
                             "response_version": version, "response_body": body.decode()}
                    with owner.lock:
                        owner.events.append(event)

            def log_message(self, *_):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def matching(self, path, context=None, event=None):
        with self.lock:
            return [item for item in self.events if item["path"] == path
                    and (context is None or item["body"].get("contextPath") == context)
                    and (event is None or item["body"].get("eventType") == event)]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def verify_wire(events, client_version):
    if not events:
        raise AssertionError("No registration traffic was recorded")
    for event in events:
        require(event["authenticated"], event)
        require(event["protocol_version"] == "1", event)
        require(event["client_version"] == client_version, event)
        require(event["status"] == 200 and event["response_body"] == "success", event)
        require(event["response_version"] == "1", event)
        dto = event["body"]
        if event["path"] in {"/shenyu-client/register-uri", "/shenyu-client/offline"}:
            require(type(dto["port"]) is int, dto)
            require(dto["namespaceId"] == NAMESPACE, dto)
            if "instanceInfo" in dto:
                require(isinstance(dto["instanceInfo"], str), dto)
                require(isinstance(json.loads(dto["instanceInfo"]), dict), dto)


def verify_mcp_wire(events, port):
    configs = {}
    for event in events:
        dto = event["body"]
        metadata = dto["metaDataRegisterDTO"]
        require(dto["namespaceId"] == metadata["namespaceId"] == NAMESPACE, dto)
        require(metadata["contextPath"] == "/mcp" and metadata["host"] == "127.0.0.1" and metadata["port"] == port, metadata)
        require(isinstance(dto["mcpConfig"], str), dto)
        config = json.loads(dto["mcpConfig"])
        require(isinstance(config["requestConfig"], str), config)
        request_config = json.loads(config["requestConfig"])
        require(request_config["argsPosition"] == request_config["requestTemplate"]["argsPosition"], request_config)
        configs[config["name"]] = config
    require(set(configs) == {"findAllOrder", "findOrderById", "findByName"}, configs)
    order = json.loads(configs["findOrderById"]["requestConfig"])
    require(order["argsPosition"] == {"id": "query"}, order)
    require(order["requestTemplate"]["url"] == "/mcp/order/findById", order)
    require(order["requestTemplate"]["method"].upper() == "GET", order)
    require(order["requestTemplate"]["headers"] == [{"key": "aaa", "value": "bbb"}], order)
    return configs


class Runtime:
    def __init__(self, root, main, output, maven_repo):
        self.root, self.main, self.output = root, main, output
        self.maven_repo = maven_repo
        self.processes = []
        self.logs = []
        self.commands = []

    def maven(self, source, arguments, name):
        command = [str(source / "mvnw"), "-B", "-ntp", *arguments]
        if self.maven_repo:
            command.append("-Dmaven.repo.local=" + str(self.maven_repo.resolve()))
        self.commands.append(command)
        print("Building " + name + "; log: " + str(self.output / (name + ".log")), flush=True)
        with (self.output / (name + ".log")).open("w") as log:
            subprocess.run(command, cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True)

    def classpath(self, module, filename):
        deps = (module / "target/runtime-classpath.txt").read_text().strip()
        return str(module / "target" / filename) + os.pathsep + deps

    def compile_probe(self, classpath):
        home = os.environ.get("JAVA_HOME")
        javac = str(Path(home) / "bin/javac") if home else "javac"
        classes = self.output / "probe-classes"
        classes.mkdir()
        command = [javac, "-source", "17", "-target", "17", "-cp", classpath, "-d", str(classes), str(self.root / "script/runtime/RuntimeProbe.java")]
        self.commands.append(command)
        with (self.output / "compile-probe.log").open("w") as log:
            subprocess.run(command, cwd=self.root, stdout=log, stderr=subprocess.STDOUT, check=True)
        return str(classes) + os.pathsep + classpath

    def probe(self, name, classpath, arguments):
        process = self.start(name, classpath, "RuntimeProbe", arguments)
        try:
            process.wait(timeout=55)
        except subprocess.TimeoutExpired:
            raise RuntimeError(name + " timed out; inspect its runtime log")
        require(process.returncode == 0, name + " failed; inspect its runtime log")
        self.processes = [(label, item) for label, item in self.processes if item is not process]
        return probe_result(self.output / (name + ".log"))
    def start(self, name, classpath, main_class, arguments):
        log = (self.output / (name + ".log")).open("w")
        self.logs.append(log)
        if main_class.startswith("org.apache.shenyu."):
            arguments = [*arguments, "--logging.level.org.apache.shenyu.register.common.utils.RegisterUtils=WARN"]
        # Main's timer rejects queued tasks below 256 MiB of free committed heap.
        # A small implicit initial heap can reject registration recovery despite a larger maximum.
        command = [java_binary(), "-Xms768m", "-Xmx1024m", "-XX:ActiveProcessorCount=4", "-Dio.netty.eventLoopThreads=4",
                   "-cp", classpath, main_class, *arguments]
        self.commands.append(command)
        process = subprocess.Popen(command, cwd=self.output, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        self.processes.append((name, process))
        return process

    @staticmethod
    def stop(process):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
                raise RuntimeError("Service required forced shutdown")

    def close(self):
        errors = []
        for name, process in reversed(self.processes):
            try:
                self.stop(process)
            except RuntimeError as error:
                errors.append(f"{name}: {error}")
        for log in self.logs:
            log.close()
        return errors


def run(root, args):
    manifest = json.loads((root / ".github/migration-source.json").read_text())
    main = (args.main_source or root / "target/foundation-source").resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    output = (root / "target/runtime-compatibility" / stamp).resolve()
    output.mkdir(parents=True)
    runtime = Runtime(root, main, output, args.maven_repo)
    report = {"kind": "source-candidate", "main_revision": manifest["main_revision"],
              "client_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "client_changes": subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).splitlines(),
              "foundation_version": manifest["foundation_version"], "client_version": manifest["client_preparation_version"],
              "java": subprocess.run([java_binary(), "-version"], text=True, capture_output=True, check=True).stderr.strip(),
              "started_at": stamp, "checks": {}, "result": "failed"}
    report["client_build_fingerprint"] = client_build_fingerprint(root)
    sockets = []
    proxy = None
    try:
        spec = importlib.util.spec_from_file_location("prepare_foundations", root / "script/prepare-foundations.py")
        preparation = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preparation)
        if not args.skip_build:
            preparation.prepare(root, main, args.maven_repo)
        if preparation.run(["git", "rev-parse", "HEAD"], main) != manifest["main_revision"]:
            raise ValueError("Main runtime source does not match the pinned commit")
        if preparation.run(["git", "status", "--porcelain", "--untracked-files=no"], main):
            raise ValueError("Main runtime source has tracked changes")
        common = ["-DskipTests", "-Dmaven.test.skip=true", "-Dmaven.javadoc.skip=true", "-Djacoco.skip=true", "-DskipRemoteResources=true"]
        profiles = "-Pexamples,runtime-compatibility"
        receipt = root / "target/runtime-build-fingerprint.txt"
        if args.skip_build and (not receipt.exists() or receipt.read_text().strip() != report["client_build_fingerprint"]):
            raise ValueError("Client build inputs changed or no build receipt exists; rerun without --skip-build")
        if not args.skip_build:
            runtime.maven(main, ["-pl", "shenyu-admin,shenyu-bootstrap", "-am", "install", *common], "build-main")
            runtime.maven(root, [profiles, "-pl", EXAMPLES, "-am", "install", *common, "-Ddocker.skip=true"], "build-client")
            for source, selected, profile, name in [(main, "shenyu-admin,shenyu-bootstrap", [], "classpath-main"),
                                                     (root, EXAMPLES, [profiles], "classpath-client")]:
                runtime.maven(source, [*profile, "-pl", selected, "org.apache.maven.plugins:maven-dependency-plugin:3.6.1:build-classpath",
                                      "-DincludeScope=runtime", "-Dmdep.outputFile=target/runtime-classpath.txt"], name)
            runtime.maven(main, ["-pl", "shenyu-admin", "org.apache.maven.plugins:maven-dependency-plugin:3.6.1:build-classpath",
                                 "-DincludeScope=test", "-Dmdep.outputFile=target/runtime-test-classpath.txt"], "classpath-zookeeper-server")
            receipt.write_text(report["client_build_fingerprint"] + "\n")
        admin_cp = runtime.classpath(main / "shenyu-admin", "shenyu-admin.jar")
        gateway_cp = runtime.classpath(main / "shenyu-bootstrap", "shenyu-bootstrap.jar")
        client_cp = runtime.classpath(root / EXAMPLE, "shenyu-examples-http.jar")
        grpc_cp = runtime.classpath(root / GRPC_EXAMPLE, "shenyu-examples-grpc.jar")
        mcp_cp = runtime.classpath(root / MCP_EXAMPLE, "shenyu-examples-mcp-" + manifest["client_preparation_version"] + ".jar")
        # ZooKeeper server needs metrics/snappy dependencies that its client POM marks provided.
        # Reuse Admin's pinned test dependencies, never add server libraries to business clients.
        server_cp = (main / "shenyu-admin/target/runtime-test-classpath.txt").read_text().strip()
        main_owned_classpath(admin_cp)
        main_owned_classpath(gateway_cp)
        main_owned_classpath(server_cp)
        probe_cp = runtime.compile_probe(gateway_cp + os.pathsep + server_cp)
        report["checks"]["main_runtime_ownership"] = True
        report["artifacts"] = [{"path": str(Path(entry)), "sha256": hashlib.sha256(Path(entry).read_bytes()).hexdigest()}
                               for entry in sorted(set(os.pathsep.join((admin_cp, gateway_cp, client_cp, grpc_cp, mcp_cp, server_cp)).split(os.pathsep)))]
        for _ in range(10):
            bound = socket.socket()
            bound.bind(("127.0.0.1", 0))
            sockets.append(bound)
        admin_port, gateway_port, proxy_port, local_port, zk_port, discovery_port, second_port, grpc_http_port, grpc_port, mcp_port = [item.getsockname()[1] for item in sockets]
        report["ports"] = dict(zip(["admin", "gateway", "registration_proxy", "local_client", "zookeeper", "discovery_client", "second_discovery_client", "grpc_http", "grpc", "mcp"],
                                   [admin_port, gateway_port, proxy_port, local_port, zk_port, discovery_port, second_port, grpc_http_port, grpc_port, mcp_port]))
        admin_url, gateway_url = f"http://127.0.0.1:{admin_port}", f"http://127.0.0.1:{gateway_port}"
        token_sync = uuid.uuid4().hex
        sockets[0].close()
        runtime.start("admin", admin_cp, "org.apache.shenyu.admin.ShenyuAdminBootstrap",
                      [f"--server.port={admin_port}", "--server.address=127.0.0.1", "--spring.profiles.active=h2",
                       "--spring.datasource.url=jdbc:h2:mem:runtime_compatibility;DB_CLOSE_DELAY=-1;MODE=MySQL;",
                       f"--shenyu.jwt.secret-key={uuid.uuid4().hex + uuid.uuid4().hex}",
                       f"--shenyu.sync.websocket.allowOrigins=ws://127.0.0.1:{gateway_port}",
                       f"--shenyu.sync.websocket.token={token_sync}", "--shenyu.register.props.checked=false"])
        wait_for("Admin readiness", lambda: request(admin_url + "/actuator/health")[0] == 200, runtime.processes)
        status, text, _ = request(admin_url + "/platform/login", {"userName": "admin", "password": "123456"})
        require(status == 200, text)
        token = json.loads(text)["data"]["token"]
        auth = {"X-Access-Token": token}

        def admin_data(path, **query):
            status, body, _ = request(admin_url + path + "?" + urlencode(query), headers=auth)
            require(status == 200, body)
            result = json.loads(body)
            require(result["code"] == 200, result)
            return result["data"]

        def admin_mutation(path, body, method="POST"):
            status, text, _ = request(admin_url + path, body, auth, method)
            require(status == 200 and json.loads(text)["code"] == 200, text)

        def enable_plugin(name):
            plugins = page("/namespace-plugin", name=name)
            plugins = [plugin for plugin in plugins if plugin["name"] == name]
            require(len(plugins) == 1, plugins)
            admin_mutation("/namespace-plugin/enabled", {"ids": [plugins[0]["id"]], "enabled": True})

        def page(path, **query):
            return admin_data(path, currentPage=1, pageSize=100, namespaceId=NAMESPACE, **query)["dataList"]

        def upstreams(context):
            rows = page("/selector", pluginId="5", name=context)
            rows = [row for row in rows if row["name"] == context]
            return None if not rows else admin_data("/selector/" + rows[0]["id"]).get("discoveryUpstreams")

        sockets[2].close()
        proxy = RecordingProxy(admin_url, proxy_port)
        sockets[1].close()
        runtime.start("gateway", gateway_cp, "org.apache.shenyu.bootstrap.ShenyuBootstrapApplication",
                      [f"--server.port={gateway_port}", "--server.address=127.0.0.1",
                       f"--shenyu.sync.websocket.urls=ws://127.0.0.1:{admin_port}/websocket",
                       f"--shenyu.sync.websocket.allowOrigin=ws://127.0.0.1:{gateway_port}",
                       f"--shenyu.sync.websocket.token={token_sync}", f"--shenyu.heartbeat.serverLists={admin_url}"])
        wait_for("gateway readiness", lambda: request(gateway_url + "/actuator/health")[0] == 200, runtime.processes)

        def client(name, context, port, discovery=False, app_name=None, expected_upstreams=None):
            app_name = app_name or name
            expected_upstreams = sorted(expected_upstreams or [f"127.0.0.1:{port}"])
            arguments = [f"--server.port={port}", "--server.address=127.0.0.1",
                         f"--shenyu.register.serverLists=http://127.0.0.1:{proxy_port}",
                         f"--shenyu.client.http.props.contextPath={context}", f"--shenyu.client.http.props.appName={app_name}",
                         "--shenyu.client.http.props.host=127.0.0.1", f"--shenyu.client.http.props.port={port}",
                         f"--shenyu.discovery.type={'zookeeper' if discovery else 'local'}"]
            if discovery:
                arguments += ["--shenyu.discovery.enable=true", "--shenyu.discovery.register=true",
                              "--shenyu.discovery.protocol=http://", f"--shenyu.discovery.serverList=127.0.0.1:{zk_port}",
                              f"--shenyu.discovery.props.name={app_name}"]
            process = runtime.start(name, client_cp, "org.apache.shenyu.examples.http.ShenyuTestHttpApplication", arguments)
            route = "/test/findByUserId?userId=7602"
            expected = wait_for(name + " readiness", lambda: response_user(f"http://127.0.0.1:{port}" + route), runtime.processes)
            wait_for(name + " metadata", lambda: any(row["path"].startswith(context + "/") for row in page("/meta-data/queryList")), runtime.processes)
            selectors = wait_for(name + " divide selector", lambda: [row for row in page("/selector", pluginId="5", name=context) if row["name"] == context], runtime.processes)
            wait_for(name + " rules", lambda: page("/rule", selectorId=selectors[0]["id"]), runtime.processes)
            wait_for(name + " upstream", lambda: sorted(row["url"] for row in (upstreams(context) or [])) == expected_upstreams, runtime.processes)
            wait_for(name + " gateway proxy", lambda: response_user(gateway_url + context + route) == expected, runtime.processes)
            wait_for(name + " gateway upstream snapshot", lambda: gateway_snapshot(output / "gateway.log", context) == expected_upstreams, runtime.processes)
            report["checks"][name + "_registered_and_proxied"] = {"selector_id": selectors[0]["id"], "response": expected}
            return process, route, expected

        sockets[3].close()
        local, route, expected = client("compat-local", "/compat-local", local_port)
        wait_for("two scheduled client heartbeats", lambda: len(proxy.matching("/shenyu-client/register-uri", "/compat-local", "HEARTBEAT")) >= 2, runtime.processes, timeout=65)
        instances = wait_for("client instance info in Admin", lambda: [row for row in page("/instance", instancePort=str(local_port)) if row.get("instanceInfo")], runtime.processes)
        require(isinstance(instances[0]["instanceInfo"], str) and isinstance(json.loads(instances[0]["instanceInfo"]), dict), instances[0])
        first_beat = instances[0]["lastHeartBeatTime"]
        wait_for("Admin heartbeat renewal", lambda: any(row["lastHeartBeatTime"] > first_beat for row in page("/instance", instancePort=str(local_port))), runtime.processes, timeout=25)
        report["checks"]["scheduled_heartbeats_and_instance_info"] = True
        runtime.stop(local)
        runtime.processes = [(name, process) for name, process in runtime.processes if process is not local]
        wait_for("authenticated offline request", lambda: proxy.matching("/shenyu-client/offline", "/compat-local", "OFFLINE"), timeout=20)
        wait_for("offline upstream removal", lambda: upstreams("/compat-local") == [], runtime.processes[:2], timeout=30)
        wait_for("offline gateway empty snapshot", lambda: gateway_snapshot(output / "gateway.log", "/compat-local") == [], runtime.processes[:2], timeout=30)
        wait_for("offline gateway convergence", lambda: gateway_empty(gateway_url + "/compat-local" + route), runtime.processes[:2], timeout=30)
        report["checks"]["local_shutdown_removed_upstream"] = True

        # Run the main-owned provider's ZooKeeper version with Admin's server test dependencies.
        sockets[4].close()
        config = output / "zookeeper.cfg"
        config.write_text(f"tickTime=2000\ndataDir={output / 'zookeeper-data'}\nclientPort={zk_port}\nclientPortAddress=127.0.0.1\nadmin.enableServer=false\n")
        zk = runtime.start("zookeeper", server_cp, "org.apache.zookeeper.server.quorum.QuorumPeerMain", [str(config)])
        wait_for("ZooKeeper readiness", lambda: listening(zk_port), [("zookeeper", zk)])
        sockets[5].close()
        discovered, zk_route, zk_expected = client("compat-zookeeper-a", "/compat-zookeeper", discovery_port, discovery=True, app_name="compat-zookeeper")
        sockets[6].close()
        second, _, _ = client("compat-zookeeper-b", "/compat-zookeeper", second_port, discovery=True, app_name="compat-zookeeper",
                              expected_upstreams=[f"127.0.0.1:{discovery_port}", f"127.0.0.1:{second_port}"])
        update = runtime.probe("registry-weight-update", probe_cp, ["registry-update", f"127.0.0.1:{zk_port}", "compat-zookeeper", str(second_port), "80"])
        wait_for("Admin registry weight update", lambda: any(row["url"] == f"127.0.0.1:{second_port}" and row["weight"] == 80
                 for row in (upstreams("/compat-zookeeper") or [])), runtime.processes)
        wait_for("gateway registry weight update", lambda: any(row["url"] == f"127.0.0.1:{second_port}" and row["weight"] == 80
                 for row in (gateway_upstream_data(output / "gateway.log", "/compat-zookeeper") or [])), runtime.processes)
        report["checks"]["zookeeper_instance_weight_update"] = update
        configs = proxy.matching("/shenyu-client/register-discoveryConfig")
        require(any(item["body"]["listenerNode"] == "/shenyu/register/instance/compat-zookeeper" for item in configs), configs)
        require(not proxy.matching("/shenyu-client/register-uri", "/compat-zookeeper"), "Discovery mode published a local URI")
        runtime.stop(discovered)
        runtime.processes = [(name, process) for name, process in runtime.processes if process is not discovered]
        wait_for("remaining ZooKeeper instance", lambda: sorted(row["url"] for row in (upstreams("/compat-zookeeper") or [])) == [f"127.0.0.1:{second_port}"], runtime.processes)
        wait_for("remaining gateway instance snapshot", lambda: gateway_snapshot(output / "gateway.log", "/compat-zookeeper") == [f"127.0.0.1:{second_port}"], runtime.processes)
        wait_for("remaining instance still proxies", lambda: response_user(gateway_url + "/compat-zookeeper" + zk_route) == zk_expected, runtime.processes)
        runtime.stop(second)
        runtime.processes = [(name, process) for name, process in runtime.processes if process is not second]
        wait_for("ZooKeeper instance removal", lambda: upstreams("/compat-zookeeper") == [], runtime.processes[:2], timeout=30)
        wait_for("discovery gateway empty snapshot", lambda: gateway_snapshot(output / "gateway.log", "/compat-zookeeper") == [], runtime.processes[:2], timeout=30)
        wait_for("discovery gateway convergence", lambda: gateway_empty(gateway_url + "/compat-zookeeper" + zk_route), runtime.processes[:2], timeout=30)
        report["checks"]["zookeeper_instance_add_remove"] = {"upstream_counts": [1, 2, 1, 0]}

        enable_plugin("grpc")
        sockets[7].close()
        sockets[8].close()
        grpc = runtime.start("grpc-client", grpc_cp, "org.apache.shenyu.examples.grpc.ShenyuTestGrpcApplication",
                             [f"--server.port={grpc_http_port}", "--server.address=127.0.0.1",
                              f"--shenyu.register.serverLists=http://127.0.0.1:{proxy_port}",
                              f"--shenyu.client.grpc.props.ipAndPort=127.0.0.1:{grpc_port}",
                              "--shenyu.client.grpc.props.host=127.0.0.1",
                              f"--shenyu.client.grpc.props.port={grpc_port}", "--logging.level.org.apache.shenyu=INFO"])
        wait_for("gRPC backend readiness", lambda: listening(grpc_port), runtime.processes)
        wait_for("gRPC metadata", lambda: any(row["path"] == "/grpc/echo" and row["rpcType"] == "grpc" for row in page("/meta-data/queryList")), runtime.processes)
        def grpc_response():
            status, body, _ = request(gateway_url + "/grpc/echo", {"data": [{"message": "migration-7602"}]})
            value = json.loads(body)
            return value if status == 200 and isinstance(value, list) and value and value[0].get("message") == "ReceivedHELLO" else None
        response = wait_for("real gRPC gateway proxy", grpc_response, runtime.processes)
        report["checks"]["grpc_registered_and_proxied"] = response
        rpc_cases = {
            "helloService/hello": ({"data": [{"data": "migration-7602"}]}, [{"data": "hello: migration-7602"}]),
            "unaryFun": ({"data": [{"text": "migration-7602"}]}, [{"text": "unaryFun response: hello gRPC"}]),
            "serverStreamingFun": ({"data": [{"text": "migration-7602"}]}, [{"text": f"serverStreamingFun response: hello {index}"} for index in range(10)]),
            "clientStreamingFun": ({"data": [{"text": "first"}, {"text": "second"}]}, [{"text": "clientStreamingFun onCompleted"}]),
            "bidiStreamingFun": ({"data": [{"text": "first"}, {"text": "second"}]}, [{"text": "bidiStreamingFun response: hello"},
                                                                                      {"text": "bidiStreamingFun response: hello"}, {"text": "bidiStreamingFun onCompleted"}]),
        }
        rpc_results = {}
        for method, (payload, expected_response) in rpc_cases.items():
            def rpc_response():
                status, body, _ = request(gateway_url + "/grpc/" + method, payload)
                value = json.loads(body)
                return value if status == 200 and value == expected_response else None
            rpc_results[method] = wait_for("gRPC " + method, rpc_response, runtime.processes)
        report["checks"]["grpc_unary_and_streaming"] = rpc_results
        runtime.stop(grpc)
        runtime.processes = [(name, process) for name, process in runtime.processes if process is not grpc]
        wait_for("gRPC offline request", lambda: proxy.matching("/shenyu-client/offline", "/grpc", "OFFLINE"), runtime.processes)
        wait_for("gRPC gateway empty snapshot", lambda: gateway_snapshot(output / "gateway.log", "/grpc") == [], runtime.processes)
        report["checks"]["grpc_shutdown_removed_upstream"] = True

        enable_plugin("mcpServer")
        sockets[9].close()
        mcp = runtime.start("mcp-client", mcp_cp, "org.apache.shenyu.examples.ShenyuTestMcpApplication",
                            [f"--server.port={mcp_port}", "--server.address=127.0.0.1",
                             f"--shenyu.register.serverLists=http://127.0.0.1:{proxy_port}"])
        wait_for("MCP example readiness", lambda: request(f"http://127.0.0.1:{mcp_port}/order/findAll")[0] == 200, runtime.processes)
        wait_for("MCP registration", lambda: len(proxy.matching("/shenyu-client/register-mcp")) == 3, runtime.processes)
        wait_for("MCP backend upstream", lambda: gateway_snapshot(output / "gateway.log", "/mcp") == [f"127.0.0.1:{mcp_port}"], runtime.processes)
        wait_for("MCP rules", lambda: any(row["name"] == "/mcp" for row in page("/selector", pluginId="61")), runtime.processes)
        configs = verify_mcp_wire(proxy.matching("/shenyu-client/register-mcp"), mcp_port)
        selectors = [row for row in page("/selector", pluginId="61") if row["name"] == "/mcp"]
        def mcp_rules():
            rows = page("/rule", selectorId=selectors[0]["id"])
            return rows if {row["name"] for row in rows} == set(configs) else None
        rules = wait_for("MCP tool rules in Admin", mcp_rules, runtime.processes)
        stored_configs = {row["name"]: json.loads(row["handle"]) for row in rules}
        require(stored_configs == configs, stored_configs)
        report["checks"]["mcp_nested_registration_preserved"] = True
        report["checks"]["mcp_registered_and_called"] = runtime.probe("mcp-tool-calls", probe_cp, ["mcp", gateway_url, "/mcp/streamablehttp"])
        runtime.stop(mcp)
        runtime.processes = [(name, process) for name, process in runtime.processes if process is not mcp]
        wait_for("MCP HTTP offline request", lambda: proxy.matching("/shenyu-client/offline", "/mcp", "OFFLINE"), runtime.processes)
        wait_for("MCP backend gateway empty snapshot", lambda: gateway_snapshot(output / "gateway.log", "/mcp") == [], runtime.processes)
        report["checks"]["mcp_backend_shutdown_removed_upstream"] = True
        verify_wire(proxy.events, manifest["client_preparation_version"])
        report["checks"]["authenticated_v1_wire_contract"] = True
        report["result"] = "passed"
    except subprocess.CalledProcessError as error:
        report["error"] = f"{Path(error.cmd[0]).name} failed with exit code {error.returncode}; inspect the build/compile logs"
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        cleanup_errors = runtime.close()
        if cleanup_errors:
            report["cleanup_errors"] = cleanup_errors
            report["result"] = "failed"
        if proxy:
            proxy.close()
            (output / "registration-traffic.json").write_text(json.dumps(proxy.events, indent=2) + "\n")
        for bound in sockets:
            bound.close()
        # Keep arguments needed to replay the run, excluding generated auth credentials.
        report["commands"] = [[item.split("=", 1)[0] + "=<per-run-secret>" if item.startswith(("--shenyu.sync.websocket.token=", "--shenyu.jwt.secret-key=")) else item
                               for item in command] for command in runtime.commands]
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Runtime compatibility {report['result']}; report: {output / 'report.json'}", flush=True)
    if report["result"] != "passed":
        print(report.get("error", report.get("cleanup_errors")), file=sys.stderr)
        return 1
    return 0


def response_user(url):
    status, body, _ = request(url)
    if status != 200:
        return None
    try:
        value = json.loads(body)
        return value if value.get("userId") == "7602" else None
    except (json.JSONDecodeError, AttributeError):
        return None


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-source", type=Path, help="Clean checkout at .github/migration-source.json's main SHA")
    parser.add_argument("--maven-repo", type=Path, help="Use the same local Maven repository for both builds")
    parser.add_argument("--skip-build", action="store_true", help="Reuse this script's existing installs and runtime classpaths")
    sys.exit(run(Path(__file__).resolve().parents[1], parser.parse_args()))
