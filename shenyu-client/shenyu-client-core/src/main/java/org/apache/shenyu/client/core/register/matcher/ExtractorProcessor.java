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

package org.apache.shenyu.client.core.register.matcher;



import org.apache.shenyu.client.core.enums.RpcTypeEnum;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * ApiAnnotationProcessor.<br>
 * Supports post-extraction and processing of client metadata.
 */
public interface ExtractorProcessor extends ApiBeanProcessor {
    
    /**
     * By default, all client pairs are supported.
     *
     * @return support type.
     * @see RpcTypeEnum
     */
    default List<String> supportedClient() {
        return Arrays.stream(RpcTypeEnum.values())
                .map(RpcTypeEnum::getName)
                .collect(Collectors.toList());
    }
}
