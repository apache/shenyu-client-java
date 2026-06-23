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


import com.sun.management.OperatingSystemMXBean;
import java.lang.management.ManagementFactory;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.HashMap;
import java.util.Map;
import oshi.SystemInfo;

/**
 * The type System info utils.
 */
public final class SystemInfoUtils {

  private static final int BYTES_IN_KB = 1024;

  private static final int BYTES_IN_MB = BYTES_IN_KB * 1024;

  private static final int BYTES_IN_GB = BYTES_IN_MB * 1024;

  private static final int DECIMAL_PLACES = 2;

  private static final RoundingMode ROUNDING_MODE = RoundingMode.HALF_UP;

  private static final String AVAILABLE_PROCESSORS = "availableProcessors";

  private static final String TOTAL_MEMORY_SIZE_GB = "totalMemorySizeGB";

  private static final String GB = "GB";

  private static final String ARCH = "arch";

  private static final String OPERATING_SYSTEM = "operatingSystem";

  /**
   * Gets system info.
   *
   * @return the system info
   */
  public static String getSystemInfo() {
    try {
      // Get host information using OSHI
      SystemInfo systemInfo = new SystemInfo();

      // Get host information
      OperatingSystemMXBean osBean =
          (OperatingSystemMXBean) ManagementFactory.getOperatingSystemMXBean();
      long totalMemory = systemInfo.getHardware().getMemory().getTotal();

      Map<String, Object> hostInfo = new HashMap<>();
      hostInfo.put(ARCH, osBean.getArch());
      hostInfo.put(OPERATING_SYSTEM, systemInfo.getOperatingSystem().toString());
      hostInfo.put(AVAILABLE_PROCESSORS, osBean.getAvailableProcessors());
      hostInfo.put(TOTAL_MEMORY_SIZE_GB, bytesToGB(totalMemory) + GB);
      return GsonUtils.getInstance().toJson(hostInfo);
    } catch (Exception e) {
        throw new RuntimeException("Error retrieving system information: " + e.getMessage(), e);
    }
  }

  /**
   * Bytes to gb double.
   *
   * @param bytesValue the bytes value
   * @return the double
   */
  private static double bytesToGB(final long bytesValue) {
    return BigDecimal.valueOf(bytesValue / (double) BYTES_IN_GB)
        .setScale(DECIMAL_PLACES, ROUNDING_MODE)
        .doubleValue();
  }
}
