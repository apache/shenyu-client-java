# shenyu-client-java

support jdk 1.8+ and spring boot 2.x

## WebSocket gateway runtime probe

The example command uses the `shenyu-example-spring-native-websocket` module in
the [Java 17 migration candidate](https://github.com/apache/shenyu-client-java/pull/16).
Build and start the application separately from ShenYu Admin and the gateway.
Enable the WebSocket plugin and wait for Admin to show the application's
`/ws-native` selector and rule. Run the command below with JDK 17 or later from the repository root.

```sh
java script/runtime/WebSocketProbe.java \
  'ws://127.0.0.1:9195/ws-native/myWebSocket?token=Jack' \
  'apache shenyu server send to Jack message : -> '
```

Use the gateway address and the full registered path. The second argument is the
prefix the application adds to its reply. The probe sends a fresh payload and
requires the exact echoed response and a normal close frame. A failed upgrade,
timeout, unexpected response, or abnormal close returns a nonzero exit status.
