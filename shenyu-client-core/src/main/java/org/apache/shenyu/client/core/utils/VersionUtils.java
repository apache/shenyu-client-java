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

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.URL;
import java.security.CodeSource;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

/**
 * Version utils.
 */
public final class VersionUtils {

    private static final Logger LOG = LoggerFactory.getLogger(VersionUtils.class);

    private static final String VERSION = getVersion(VersionUtils.class, "1.0.0");

    private static final String JAR = ".jar";

    private VersionUtils() {
    }

    /**
     * Gets version.
     *
     * @return the version
     */
    public static String getVersion() {
        return VERSION;
    }

    /**
     * Gets version.
     *
     * @param cls            the class
     * @param defaultVersion the default version
     * @return the version
     */
    public static String getVersion(final Class<?> cls, final String defaultVersion) {
        String version = cls.getPackage().getImplementationVersion();
        if (StringUtils.isBlank(version)) {
            version = cls.getPackage().getSpecificationVersion();
        }
        if (StringUtils.isNoneBlank(version)) {
            return version;
        }
        CodeSource codeSource = cls.getProtectionDomain().getCodeSource();
        if (Objects.isNull(codeSource)) {
            LOG.info("No codeSource for class {} when getVersion, use default version {}", cls.getName(), defaultVersion);
            return defaultVersion;
        }
        String file = codeSource.getLocation().getFile();
        if (Objects.nonNull(file) && file.endsWith(JAR)) {
            file = file.substring(0, file.length() - 4);
            int index = file.lastIndexOf('/');
            if (index >= 0) {
                file = file.substring(index + 1);
            }
            index = file.indexOf("-");
            if (index >= 0) {
                file = file.substring(index + 1);
            }
            while (StringUtils.isNoneBlank(file) && !Character.isDigit(file.charAt(0))) {
                index = file.indexOf("-");
                if (index < 0) {
                    break;
                }
                file = file.substring(index + 1);
            }
            version = file;
        }
        return StringUtils.isBlank(version) ? defaultVersion : version;
    }

    /**
     * Check duplicate class resources.
     *
     * @param cls class
     */
    public static void checkDuplicate(final Class<?> cls) {
        try {
            String path = cls.getName().replace('.', '/') + ".class";
            Set<String> files = readResources(path, cls);
            if (files.size() > 1) {
                String error = "Duplicate class " + path + " in " + files.size() + " jar " + files;
                LOG.error("checkDuplicate error,{}", error);
            }
        } catch (Throwable e) {
            LOG.error("checkDuplicate error,msg :{}", e.getMessage(), e);
        }
    }

    private static Set<String> readResources(final String path, final Class<?> cls) throws IOException {
        Enumeration<URL> urls = cls.getClassLoader().getResources(path);
        Set<String> files = new HashSet<>();
        while (urls.hasMoreElements()) {
            URL url = urls.nextElement();
            if (Objects.nonNull(url) && StringUtils.isNotEmpty(url.getFile())) {
                files.add(url.getFile());
            }
        }
        return files;
    }
}
