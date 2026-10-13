/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.shenyu.register.client.http;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpServer;
import org.apache.shenyu.common.constant.Constants;
import org.apache.shenyu.register.client.http.utils.ClientRegisterUtils;
import org.apache.shenyu.register.client.http.utils.RuntimeUtils;
import org.apache.shenyu.register.common.config.ShenyuRegisterCenterConfig;
import org.apache.shenyu.register.common.dto.ApiDocRegisterDTO;
import org.apache.shenyu.register.common.dto.DiscoveryConfigRegisterDTO;
import org.apache.shenyu.register.common.dto.InstanceBeatInfoDTO;
import org.apache.shenyu.register.common.dto.McpToolsRegisterDTO;
import org.apache.shenyu.register.common.dto.MetaDataRegisterDTO;
import org.apache.shenyu.register.common.dto.URIRegisterDTO;
import org.apache.shenyu.register.common.protocol.RegistrationProtocol;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.MockedStatic;

import java.io.InputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicReference;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.mockStatic;

/**
 * Capture real SDK HTTP requests against fixtures loaded from the main-owned protocol JAR.
 */
class RegistrationWireContractTest {

    private final Gson gson = new Gson();

    @ParameterizedTest
    @MethodSource("requests")
    void emitsV1RequestsAcceptedByHeaderlessAdminResponses(final String fixture, final String path) throws Exception {
        String json;
        try (InputStream input = Objects.requireNonNull(getClass().getResourceAsStream("/registration/v1/" + fixture + ".json"))) {
            json = new String(input.readAllBytes(), StandardCharsets.UTF_8);
        }
        AtomicReference<JsonObject> captured = new AtomicReference<>();
        AtomicReference<Headers> capturedHeaders = new AtomicReference<>();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext(RegistrationProtocol.LOGIN_PATH, exchange -> {
            exchange.getRequestBody().readAllBytes();
            byte[] response = "{\"code\":200,\"data\":{\"token\":\"fixture-token\"}}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        server.createContext(path, exchange -> {
            assertEquals("POST", exchange.getRequestMethod());
            captured.set(JsonParser.parseString(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8)).getAsJsonObject());
            capturedHeaders.set(exchange.getRequestHeaders());
            byte[] response = "success".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        server.start();
        try (MockedStatic<RuntimeUtils> runtime = mockStatic(RuntimeUtils.class)) {
            runtime.when(() -> RuntimeUtils.listenByOther(anyInt())).thenReturn(false);
            ShenyuRegisterCenterConfig config = new ShenyuRegisterCenterConfig();
            config.setServerLists("http://127.0.0.1:" + server.getAddress().getPort());
            config.getProps().setProperty(Constants.USER_NAME, "fixture-user");
            config.getProps().setProperty(Constants.PASS_WORD, "fixture-password");
            HttpClientRegisterRepository repository = new HttpClientRegisterRepository(config);
            send(repository, fixture, json);
            assertNotNull(captured.get());
            assertEquals(JsonParser.parseString(json), captured.get());
            assertEquals("1", capturedHeaders.get().getFirst(RegistrationProtocol.VERSION_HEADER));
            assertEquals("fixture-token", capturedHeaders.get().getFirst(Constants.X_ACCESS_TOKEN));
            assertEquals(ClientRegisterUtils.class.getPackage().getImplementationVersion(),
                    capturedHeaders.get().getFirst(RegistrationProtocol.CLIENT_VERSION_HEADER));
        } finally {
            server.stop(0);
        }
    }

    private void send(final HttpClientRegisterRepository repository, final String fixture, final String json) {
        switch (fixture) {
            case "metadata" -> repository.doPersistInterface(gson.fromJson(json, MetaDataRegisterDTO.class));
            case "uri" -> repository.doPersistURI(gson.fromJson(json, URIRegisterDTO.class));
            case "uri-heartbeat" -> repository.sendHeartbeat(gson.fromJson(json, URIRegisterDTO.class));
            case "offline" -> repository.offline(gson.fromJson(json, URIRegisterDTO.class));
            case "heartbeat" -> repository.sendHeartbeat(gson.fromJson(json, InstanceBeatInfoDTO.class));
            case "api-doc" -> repository.doPersistApiDoc(gson.fromJson(json, ApiDocRegisterDTO.class));
            case "mcp" -> repository.doPersistMcpTools(gson.fromJson(json, McpToolsRegisterDTO.class));
            case "discovery-config" -> repository.doPersistDiscoveryConfig(gson.fromJson(json, DiscoveryConfigRegisterDTO.class));
            default -> throw new IllegalArgumentException(fixture);
        }
    }

    private static Stream<Arguments> requests() {
        return Stream.of(Arguments.of("metadata", RegistrationProtocol.META_PATH), Arguments.of("uri", RegistrationProtocol.URI_PATH),
                Arguments.of("uri-heartbeat", RegistrationProtocol.URI_PATH), Arguments.of("offline", RegistrationProtocol.OFFLINE_PATH),
                Arguments.of("heartbeat", RegistrationProtocol.BEAT_URI_PATH), Arguments.of("api-doc", RegistrationProtocol.API_DOC_PATH),
                Arguments.of("mcp", RegistrationProtocol.MCP_TOOLS_PATH), Arguments.of("discovery-config", RegistrationProtocol.DISCOVERY_CONFIG_PATH));
    }
}
