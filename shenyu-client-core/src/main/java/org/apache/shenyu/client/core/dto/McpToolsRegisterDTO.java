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

import org.apache.shenyu.client.core.type.DataType;
import org.apache.shenyu.client.core.type.DataTypeParent;

/**
 * Mcp tools register dto.
 */
public class McpToolsRegisterDTO implements DataTypeParent {

    private MetaDataRegisterDTO metaDataRegisterDTO;

    private String namespaceId;

    private String mcpConfig;

    /**
     * get meta data register dto.
     *
     * @return metaDataRegisterDTO
     */
    public MetaDataRegisterDTO getMetaDataRegisterDTO() {
        return metaDataRegisterDTO;
    }

    /**
     * set meta data register dto.
     *
     * @param metaDataRegisterDTO metaDataRegisterDTO
     */
    public void setMetaDataRegisterDTO(final MetaDataRegisterDTO metaDataRegisterDTO) {
        this.metaDataRegisterDTO = metaDataRegisterDTO;
    }

    /**
     * get mcp config.
     *
     * @return mcpConfig
     */
    public String getMcpConfig() {
        return mcpConfig;
    }

    /**
     * set mcp config.
     *
     * @param mcpConfig mcpConfig
     */
    public void setMcpConfig(final String mcpConfig) {
        this.mcpConfig = mcpConfig;
    }

    /**
     * get namespace id.
     *
     * @return namespaceId
     */
    public String getNamespaceId() {
        return namespaceId;
    }

    /**
     * set namespace id.
     *
     * @param namespaceId namespaceId
     */
    public void setNamespaceId(final String namespaceId) {
        this.namespaceId = namespaceId;
    }

    @Override
    public DataType getType() {
        return DataType.MCP_TOOLS;
    }
}
