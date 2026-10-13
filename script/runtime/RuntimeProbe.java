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

import com.google.gson.JsonObject;
import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.client.transport.HttpClientStreamableHttpTransport;
import io.modelcontextprotocol.spec.McpSchema;
import org.apache.shenyu.common.utils.GsonUtils;
import org.apache.shenyu.registry.api.ShenyuInstanceRegisterRepository;
import org.apache.shenyu.registry.core.ShenyuInstanceRegisterRepositoryFactory;
import org.apache.shenyu.registry.api.config.RegisterConfig;
import org.apache.shenyu.registry.api.entity.InstanceEntity;

import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;

/**
 * Client-owned runtime assertions using main's registry API and MCP SDK.
 */
public final class RuntimeProbe {

    private RuntimeProbe() {
    }

    /**
     * Execute an isolated runtime assertion and emit its JSON evidence.
     *
     * @param args operation and target
     * @throws Exception on assertion or transport failure
     */
    public static void main(final String[] args) throws Exception {
        if ("registry-update".equals(args[0])) {
            updateRegistry(args);
        } else if ("mcp".equals(args[0])) {
            verifyMcp(args);
        } else {
            throw new IllegalArgumentException("Unknown runtime probe operation");
        }
    }

    private static void updateRegistry(final String[] args) {
        ShenyuInstanceRegisterRepository repository = ShenyuInstanceRegisterRepositoryFactory.loadRepository("zookeeper");
        Properties properties = new Properties();
        properties.setProperty("name", args[2]);
        repository.init(new RegisterConfig("zookeeper", args[1], properties));
        try {
            int port = Integer.parseInt(args[3]);
            InstanceEntity instance = repository.selectInstances(args[2]).stream()
                    .filter(item -> "127.0.0.1".equals(item.getHost()) && port == item.getPort()).findFirst().orElseThrow();
            instance.setWeight(Integer.parseInt(args[4]));
            repository.persistInstance(instance);
            System.out.println("PROBE_RESULT=" + GsonUtils.getInstance().toJson(instance));
        } finally {
            repository.close();
        }
    }

    private static void verifyMcp(final String[] args) {
        HttpClientStreamableHttpTransport transport = HttpClientStreamableHttpTransport.builder(args[1])
                .endpoint(args[2]).supportedProtocolVersions(List.of("2025-03-26"))
                .openConnectionOnStartup(false).build();
        try (McpSyncClient client = McpClient.sync(transport).requestTimeout(Duration.ofSeconds(15))
                .initializationTimeout(Duration.ofSeconds(15)).build()) {
            McpSchema.InitializeResult initialization = client.initialize();
            McpSchema.ListToolsResult tools = client.listTools();
            if (tools.tools().stream().noneMatch(tool -> "findAllOrder".equals(tool.name()))
                    || tools.tools().stream().noneMatch(tool -> "findOrderById".equals(tool.name()))) {
                throw new IllegalStateException("Registered MCP tools are missing: " + tools);
            }
            McpSchema.CallToolResult all = client.callTool(new McpSchema.CallToolRequest("findAllOrder", Map.of()));
            String allText = content(all);
            if (!allText.contains("hello apache shenyu , mcp findAll success")) {
                throw new IllegalStateException("MCP did not reach the real backend: " + allText);
            }
            McpSchema.CallToolResult order = client.callTool(new McpSchema.CallToolRequest("findOrderById", Map.of("id", "7602")));
            String orderText = content(order);
            JsonObject orderJson = GsonUtils.getInstance().fromJson(orderText, JsonObject.class);
            if (!orderJson.has("id") || !"7602".equals(orderJson.get("id").getAsString())) {
                throw new IllegalStateException("MCP query argument did not reach the backend: " + orderText);
            }
            Map<String, Object> evidence = new HashMap<>();
            evidence.put("protocol", initialization.protocolVersion());
            evidence.put("tools", tools.tools().stream().map(McpSchema.Tool::name).toList());
            evidence.put("findAllOrder", allText);
            evidence.put("findOrderById", orderText);
            System.out.println("PROBE_RESULT=" + GsonUtils.getInstance().toJson(evidence));
        }
    }

    private static String content(final McpSchema.CallToolResult result) {
        if (Boolean.TRUE.equals(result.isError())) {
            throw new IllegalStateException("MCP tool call failed: " + result);
        }
        return result.content().stream().filter(McpSchema.TextContent.class::isInstance)
                .map(McpSchema.TextContent.class::cast).map(McpSchema.TextContent::text)
                .reduce("", String::concat);
    }
}
