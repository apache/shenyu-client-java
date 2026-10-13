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

"""Reject runtime evidence that could incorrectly certify the migration."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("runtime", Path(__file__).with_name("verify-runtime.py"))
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


class RuntimeTest(unittest.TestCase):
    def valid_event(self):
        return {"path": "/shenyu-client/register-uri", "body": {"port": 8189, "namespaceId": RUNTIME.NAMESPACE,
                "instanceInfo": '{"pid":"123"}'}, "status": 200, "protocol_version": "1", "client_version": "candidate",
                "authenticated": True, "response_version": "1", "response_body": "success"}

    def test_gateway_beat_is_main_owned(self):
        RUNTIME.main_owned_classpath("/repo/shenyu-register-client-beat-2.7.2.jar")
        RUNTIME.main_owned_classpath("/repo/shenyu-spring-boot-starter-client-beat-2.7.2.jar")

    def test_main_business_client_dependency_fails(self):
        for artifact in ["shenyu-client-core", "shenyu-register-client-http", "shenyu-spring-boot-starter-client-springmvc"]:
            with self.subTest(artifact=artifact), self.assertRaises(ValueError):
                RUNTIME.main_owned_classpath("/repo/" + artifact + "-2.7.2.jar")

    def test_real_wire_shape_passes(self):
        RUNTIME.verify_wire([self.valid_event()], "candidate")

    def test_wrong_wire_port_and_instance_types_fail(self):
        for field, value in [("port", "8189"), ("port", True), ("instanceInfo", {}), ("namespaceId", "other")]:
            event = self.valid_event()
            event["body"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                RUNTIME.verify_wire([event], "candidate")

    def test_missing_auth_version_or_plain_success_fails(self):
        for field, value in [("authenticated", False), ("protocol_version", None), ("client_version", "foundation"),
                             ("response_version", None), ("status", 401), ("response_body", '"success"')]:
            event = self.valid_event()
            event[field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                RUNTIME.verify_wire([event], "candidate")

    def test_empty_traffic_cannot_pass(self):
        with self.assertRaises(AssertionError):
            RUNTIME.verify_wire([], "candidate")

    def test_process_exit_cannot_pass_a_ready_condition(self):
        process = Mock()
        process.poll.return_value = 0
        process.returncode = 0
        with self.assertRaisesRegex(RuntimeError, "exited"):
            RUNTIME.wait_for("readiness", lambda: True, [("gateway", process)])

    def test_stopped_backend_is_not_gateway_convergence(self):
        for response in [(502, '{}', {}), (200, '{"code":-121}', {}), (200, '{"userId":"7602"}', {})]:
            with patch.object(RUNTIME, "request", return_value=response):
                self.assertFalse(RUNTIME.gateway_empty("http://unused"))
        with patch.object(RUNTIME, "request", return_value=(200, '{"code":-119}', {})):
            self.assertTrue(RUNTIME.gateway_empty("http://unused"))

    def test_gateway_latest_snapshot_is_namespace_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "gateway.log"
            frames = []
            for namespace, upstreams in [(RUNTIME.NAMESPACE, [{"url":"127.0.0.1:8189"}]), ("other", []), (RUNTIME.NAMESPACE, [])]:
                frames.append({"groupType":"DISCOVER_UPSTREAM", "data":[{"selectorName":"/candidate", "namespaceId":namespace,
                                                                      "upstreamDataList":upstreams}]})
            log.write_text("\n".join("logger handleResult(" + json.dumps(frame, separators=(",", ":")) + ")" for frame in frames[:2]))
            self.assertEqual(["127.0.0.1:8189"], RUNTIME.gateway_snapshot(log, "/candidate"))
            with log.open("a") as output:
                output.write("\nlogger handleResult(" + json.dumps(frames[2], separators=(",", ":")) + ")")
            self.assertEqual([], RUNTIME.gateway_snapshot(log, "/candidate"))
            self.assertIsNone(RUNTIME.gateway_snapshot(log, "/absent"))

    def test_changed_client_build_inputs_invalidate_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            source = root / "client/src/main/java/Client.java"
            source.parent.mkdir(parents=True)
            source.write_text("class Client {}")
            original = RUNTIME.client_build_fingerprint(root)
            (root / "runner.py").write_text("# runner-only change")
            self.assertEqual(original, RUNTIME.client_build_fingerprint(root))
            source.write_text("class Client { int port; }")
            self.assertNotEqual(original, RUNTIME.client_build_fingerprint(root))

    def test_colored_probe_result_is_valid_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "probe.log"
            log.write_text('logger initialization\n\x1b[0;39mPROBE_RESULT={"weight":80}\n')
            self.assertEqual({"weight": 80}, RUNTIME.probe_result(log))

    def test_missing_or_duplicate_probe_results_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "probe.log"
            for text in ['logger only\n', 'PROBE_RESULT={}\nPROBE_RESULT={}\n']:
                log.write_text(text)
                with self.assertRaises(AssertionError):
                    RUNTIME.probe_result(log)

    def mcp_events(self):
        events = []
        for name in ["findAllOrder", "findOrderById", "findByName"]:
            arguments = {"id": "query"} if name == "findOrderById" else {}
            template = {"url": "/mcp/order/findById", "method": "get", "argsPosition": arguments,
                        "headers": [{"key": "aaa", "value": "bbb"}]}
            config = {"name": name, "requestConfig": json.dumps({"requestTemplate": template, "argsPosition": arguments})}
            events.append({"body": {"namespaceId": RUNTIME.NAMESPACE, "metaDataRegisterDTO": {
                "namespaceId": RUNTIME.NAMESPACE, "contextPath": "/mcp", "host": "127.0.0.1", "port": 8150},
                "mcpConfig": json.dumps(config)}})
        return events

    def test_mcp_nested_string_config_and_namespace_are_preserved(self):
        self.assertEqual({"findAllOrder", "findOrderById", "findByName"}, set(RUNTIME.verify_mcp_wire(self.mcp_events(), 8150)))

    def test_mcp_bad_namespace_or_placeholder_port_fails(self):
        for field, value in [("namespaceId", "other"), ("port", -1)]:
            events = self.mcp_events()
            events[0]["body"]["metaDataRegisterDTO"][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                RUNTIME.verify_mcp_wire(events, 8150)

    def test_mcp_argument_position_must_match_the_backend_query(self):
        events = self.mcp_events()
        config = json.loads(events[1]["body"]["mcpConfig"])
        request = json.loads(config["requestConfig"])
        request["argsPosition"]["id"] = "path"
        request["requestTemplate"]["argsPosition"]["id"] = "path"
        config["requestConfig"] = json.dumps(request)
        events[1]["body"]["mcpConfig"] = json.dumps(config)
        with self.assertRaises(AssertionError):
            RUNTIME.verify_mcp_wire(events, 8150)


if __name__ == "__main__":
    unittest.main()
