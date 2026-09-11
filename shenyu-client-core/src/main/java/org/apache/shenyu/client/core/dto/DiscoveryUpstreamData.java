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

import com.fasterxml.jackson.annotation.JsonFormat;

import java.sql.Timestamp;

/**
 * Discovery upstream data used by client-side instance discovery registration.
 */
public class DiscoveryUpstreamData {

    private String id;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Timestamp dateCreated;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Timestamp dateUpdated;

    private String discoveryHandlerId;

    private String protocol;

    private String url;

    private int status;

    private int weight;

    private String props;

    private String namespaceId;

    public String getId() {
        return id;
    }

    public void setId(final String id) {
        this.id = id;
    }

    public Timestamp getDateCreated() {
        return dateCreated;
    }

    public void setDateCreated(final Timestamp dateCreated) {
        this.dateCreated = dateCreated;
    }

    public Timestamp getDateUpdated() {
        return dateUpdated;
    }

    public void setDateUpdated(final Timestamp dateUpdated) {
        this.dateUpdated = dateUpdated;
    }

    public String getDiscoveryHandlerId() {
        return discoveryHandlerId;
    }

    public void setDiscoveryHandlerId(final String discoveryHandlerId) {
        this.discoveryHandlerId = discoveryHandlerId;
    }

    public String getProtocol() {
        return protocol;
    }

    public void setProtocol(final String protocol) {
        this.protocol = protocol;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(final String url) {
        this.url = url;
    }

    public int getStatus() {
        return status;
    }

    public void setStatus(final int status) {
        this.status = status;
    }

    public int getWeight() {
        return weight;
    }

    public void setWeight(final int weight) {
        this.weight = weight;
    }

    public String getProps() {
        return props;
    }

    public void setProps(final String props) {
        this.props = props;
    }

    public String getNamespaceId() {
        return namespaceId;
    }

    public void setNamespaceId(final String namespaceId) {
        this.namespaceId = namespaceId;
    }
}
