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

package org.apache.shenyu.client.core.utils;

import java.lang.management.ManagementFactory;
import java.lang.management.OperatingSystemMXBean;
import java.util.HashMap;
import java.util.Map;

/**
 * Java 8 compatible system information helper for heartbeat payloads.
 */
public final class SystemInfoUtils {

    private SystemInfoUtils() {
    }

    /**
     * Gets system info.
     *
     * @return system info json
     */
    public static String getSystemInfo() {
        OperatingSystemMXBean osBean = ManagementFactory.getOperatingSystemMXBean();
        Map<String, Object> hostInfo = new HashMap<>(4);
        hostInfo.put("arch", osBean.getArch());
        hostInfo.put("operatingSystem", osBean.getName());
        hostInfo.put("availableProcessors", osBean.getAvailableProcessors());
        hostInfo.put("systemLoadAverage", osBean.getSystemLoadAverage());
        return GsonUtils.getInstance().toJson(hostInfo);
    }
}
