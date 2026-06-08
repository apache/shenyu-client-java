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

package org.apache.shenyu.client.core.dto;

/**
 * Bootstrap heartbeat payload.
 */
public class InstanceBeatInfoDTO {

    private String instanceIp;

    private String instancePort;

    private String instanceType;

    private String instanceInfo;

    private String namespaceId;

    public String getInstanceIp() {
        return instanceIp;
    }

    public void setInstanceIp(final String instanceIp) {
        this.instanceIp = instanceIp;
    }

    public String getInstancePort() {
        return instancePort;
    }

    public void setInstancePort(final String instancePort) {
        this.instancePort = instancePort;
    }

    public String getInstanceType() {
        return instanceType;
    }

    public void setInstanceType(final String instanceType) {
        this.instanceType = instanceType;
    }

    public String getInstanceInfo() {
        return instanceInfo;
    }

    public void setInstanceInfo(final String instanceInfo) {
        this.instanceInfo = instanceInfo;
    }

    public String getNamespaceId() {
        return namespaceId;
    }

    public void setNamespaceId(final String namespaceId) {
        this.namespaceId = namespaceId;
    }
}
