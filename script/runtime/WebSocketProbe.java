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

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.time.Duration;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * Exercises a text echo endpoint through the gateway using only the JDK.
 */
public final class WebSocketProbe {

    private static final int TIMEOUT_SECONDS = 5;

    private WebSocketProbe() {
    }

    /**
     * Connect to the supplied gateway URL and expect the fixture's prefix followed by the payload.
     *
     * @param args gateway WebSocket URL and expected response prefix
     * @throws Exception if the handshake, message exchange or close fails
     */
    public static void main(final String[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("Usage: java WebSocketProbe.java <gateway-ws-url> <response-prefix>");
        }
        URI endpoint = URI.create(args[0]);
        String payload = "shenyu-runtime-" + UUID.randomUUID();
        EchoListener listener = new EchoListener();
        WebSocket socket = await(HttpClient.newHttpClient()
                .newWebSocketBuilder()
                .connectTimeout(Duration.ofSeconds(TIMEOUT_SECONDS))
                .buildAsync(endpoint, listener), "WebSocket handshake");
        try {
            await(socket.sendText(payload, true), "sending the text message");
            if (!await(listener.message, "receiving the echo").equals(args[1] + payload)) {
                throw new IllegalStateException("Gateway returned an unexpected text echo");
            }
            await(socket.sendClose(WebSocket.NORMAL_CLOSURE, ""), "sending the close frame");
            int status = await(listener.closeStatus, "receiving the close frame");
            if (status != WebSocket.NORMAL_CLOSURE) {
                throw new IllegalStateException("Gateway returned close status " + status);
            }
        } finally {
            socket.abort();
        }
        System.out.println("WebSocket gateway handshake, text echo and normal close passed");
    }

    private static <T> T await(final CompletableFuture<T> future, final String phase) throws InterruptedException {
        try {
            return future.get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
        } catch (ExecutionException | TimeoutException ex) {
            future.cancel(true);
            throw new IllegalStateException("Failed " + phase, ex);
        }
    }

    private static final class EchoListener implements WebSocket.Listener {

        private final CompletableFuture<String> message = new CompletableFuture<>();

        private final CompletableFuture<Integer> closeStatus = new CompletableFuture<>();

        private final StringBuilder text = new StringBuilder();

        @Override
        public CompletionStage<?> onText(final WebSocket socket, final CharSequence data, final boolean last) {
            text.append(data);
            if (last) {
                message.complete(text.toString());
                text.setLength(0);
            }
            socket.request(1);
            return null;
        }

        @Override
        public CompletionStage<?> onClose(final WebSocket socket, final int status, final String reason) {
            message.completeExceptionally(new IllegalStateException("Peer closed before sending a complete text echo, status " + status));
            closeStatus.complete(status);
            return null;
        }

        @Override
        public void onError(final WebSocket socket, final Throwable error) {
            message.completeExceptionally(error);
            closeStatus.completeExceptionally(error);
        }
    }
}
