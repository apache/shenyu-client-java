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

package org.apache.shenyu.client.core.register.registrar;

import org.apache.shenyu.client.core.enums.RpcTypeEnum;
import org.apache.shenyu.client.core.register.ClientRegisterConfig;

public class TestClientRegisterConfig implements ClientRegisterConfig {
    @Override
    public Integer getPort() {
        return -1;
    }

    @Override
    public String getHost() {
        return "127.0.0.1";
    }

    @Override
    public String getAppName() {
        return "test";
    }

    @Override
    public String getContextPath() {
        return "testContext";
    }

    @Override
    public String getIpAndPort() {
        return "127.0.0.1:80";
    }

    @Override
    public Boolean getAddPrefixed() {
        return false;
    }

    @Override
    public RpcTypeEnum getRpcTypeEnum() {
        return RpcTypeEnum.HTTP;
    }
}
