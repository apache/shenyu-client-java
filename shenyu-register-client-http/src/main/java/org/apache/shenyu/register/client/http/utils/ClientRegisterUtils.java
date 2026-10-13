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

package org.apache.shenyu.register.client.http.utils;

import okhttp3.Headers;
import org.apache.commons.lang3.StringUtils;
import org.apache.shenyu.common.constant.Constants;
import org.apache.shenyu.register.common.protocol.RegistrationProtocol;
import org.apache.shenyu.register.common.utils.OkHttpTools;
import org.apache.shenyu.register.common.utils.RegisterUtils;

import java.io.IOException;
import java.util.Objects;
import java.util.Optional;

/**
 * Business-client request headers and the existing v1 text response contract.
 * Shared HTTP transport and login remain main-owned; client version identifies this SDK JAR.
 */
public final class ClientRegisterUtils {

    private ClientRegisterUtils() {
    }

    /**
     * Send a registration request.
     *
     * @param json request JSON
     * @param url Admin endpoint
     * @param type registration type
     * @param token access token
     * @throws IOException on transport or non-success response
     */
    public static void doRegister(final String json, final String url, final String type, final String token) throws IOException {
        post(json, url, type, token);
    }

    /**
     * Send a registration request without an access token.
     *
     * @param json request JSON
     * @param url Admin endpoint
     * @param type registration type
     * @throws IOException on transport or non-success response
     */
    public static void doRegister(final String json, final String url, final String type) throws IOException {
        RegisterUtils.doRegister(json, url, type);
    }

    /**
     * Send a heartbeat request.
     *
     * @param json request JSON
     * @param url Admin endpoint
     * @param type heartbeat type
     * @param token access token
     * @throws IOException on transport or non-success response
     */
    public static void doHeartBeat(final String json, final String url, final String type, final String token) throws IOException {
        post(json, url, type, token);
    }

    /**
     * Send an offline request.
     *
     * @param json request JSON
     * @param url Admin endpoint
     * @param token access token
     * @throws IOException on transport or non-success response
     */
    public static void doUnregister(final String json, final String url, final String token) throws IOException {
        post(json, url, Constants.URI, token);
    }

    /**
     * Log in using the existing Admin authentication contract.
     *
     * @param username user name
     * @param password password
     * @param url login endpoint
     * @return access token when login succeeds
     * @throws IOException on transport failure
     */
    public static Optional<Object> doLogin(final String username, final String password, final String url) throws IOException {
        return RegisterUtils.doLogin(username, password, url);
    }

    private static void post(final String json, final String url, final String type, final String token) throws IOException {
        if (StringUtils.isBlank(token)) {
            return;
        }
        Headers.Builder headers = new Headers.Builder().add(Constants.X_ACCESS_TOKEN, token)
                .add(RegistrationProtocol.VERSION_HEADER, RegistrationProtocol.V1);
        String clientVersion = ClientRegisterUtils.class.getPackage().getImplementationVersion();
        if (StringUtils.isNotBlank(clientVersion)) {
            headers.add(RegistrationProtocol.CLIENT_VERSION_HEADER, clientVersion);
        }
        String response = OkHttpTools.getInstance().post(url, json, headers.build());
        if (!Objects.equals(RegistrationProtocol.SUCCESS, response)) {
            throw new IOException("Admin returned a non-success response for " + type + " at " + url);
        }
    }
}
