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

import org.springframework.core.DefaultParameterNameDiscoverer;
import org.springframework.core.ParameterNameDiscoverer;
import org.springframework.web.bind.annotation.CookieValue;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;

import java.lang.annotation.Annotation;
import java.lang.reflect.Method;
import java.lang.reflect.Parameter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * Request method utils.
 */
public final class RequestMethodUtils {

    private static final ParameterNameDiscoverer PARAMETER_NAME_DISCOVERER = new DefaultParameterNameDiscoverer();

    private RequestMethodUtils() {
    }

    /**
     * Get supported method types from method.
     *
     * @param method method
     * @return the list of method type
     */
    public static List<String> getRequestMethodTypes(final Method method) {
        if (method.isAnnotationPresent(GetMapping.class)) {
            return Collections.singletonList("GET");
        }
        if (method.isAnnotationPresent(PostMapping.class)) {
            return Collections.singletonList("POST");
        }
        if (method.isAnnotationPresent(PutMapping.class)) {
            return Collections.singletonList("PUT");
        }
        if (method.isAnnotationPresent(DeleteMapping.class)) {
            return Collections.singletonList("DELETE");
        }
        if (method.isAnnotationPresent(PatchMapping.class)) {
            return Collections.singletonList("PATCH");
        }
        if (method.isAnnotationPresent(RequestMapping.class)) {
            RequestMapping rm = method.getAnnotation(RequestMapping.class);
            RequestMethod[] requestMethods = rm.method();
            if (requestMethods.length == 0) {
                return Arrays.asList("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD");
            }
            return Arrays.stream(requestMethods)
                    .map(Enum::name)
                    .collect(Collectors.toList());
        }
        return Collections.emptyList();
    }

    /**
     * Get the parameter position list.
     *
     * @param method method
     * @return positionList
     */
    public static List<String> getParameterPositions(final Method method) {
        List<String> positions = new ArrayList<>();
        Annotation[][] parameterAnnotations = method.getParameterAnnotations();

        for (Annotation[] annotations : parameterAnnotations) {
            String position = "query";

            for (Annotation annotation : annotations) {
                if (annotation instanceof PathVariable) {
                    position = "path";
                    break;
                } else if (annotation instanceof RequestParam) {
                    position = "query";
                    break;
                } else if (annotation instanceof RequestBody) {
                    position = "body";
                    break;
                } else if (annotation instanceof RequestHeader) {
                    position = "header";
                    break;
                } else if (annotation instanceof CookieValue) {
                    position = "cookie";
                    break;
                }
            }

            positions.add(position);
        }

        return positions;
    }

    /**
     * Get the parameter names.
     *
     * @param method method
     * @return the array of parameter names
     */
    public static String[] getParameterNames(final Method method) {
        Parameter[] parameters = method.getParameters();
        String[] namesFromDiscoverer = PARAMETER_NAME_DISCOVERER.getParameterNames(method);

        String[] result = new String[parameters.length];

        for (int i = 0; i < parameters.length; i++) {
            String nameFromAnnotation = getNameFromSpringAnnotation(parameters[i].getAnnotations());

            if (Objects.nonNull(nameFromAnnotation) && !nameFromAnnotation.isEmpty()) {
                result[i] = nameFromAnnotation;
            } else if (Objects.nonNull(namesFromDiscoverer) && namesFromDiscoverer.length > i) {
                result[i] = namesFromDiscoverer[i];
            } else {
                result[i] = "arg" + i;
            }
        }
        return result;
    }

    private static String getNameFromSpringAnnotation(final Annotation[] annotations) {
        for (Annotation annotation : annotations) {
            if (annotation instanceof RequestParam) {
                RequestParam requestParam = (RequestParam) annotation;
                if (!requestParam.name().isEmpty()) {
                    return requestParam.name();
                }
                if (!requestParam.value().isEmpty()) {
                    return requestParam.value();
                }
            } else if (annotation instanceof PathVariable) {
                PathVariable pathVariable = (PathVariable) annotation;
                if (!pathVariable.name().isEmpty()) {
                    return pathVariable.name();
                }
                if (!pathVariable.value().isEmpty()) {
                    return pathVariable.value();
                }
            } else if (annotation instanceof RequestHeader) {
                RequestHeader requestHeader = (RequestHeader) annotation;
                if (!requestHeader.name().isEmpty()) {
                    return requestHeader.name();
                }
                if (!requestHeader.value().isEmpty()) {
                    return requestHeader.value();
                }
            } else if (annotation instanceof CookieValue) {
                CookieValue cookieValue = (CookieValue) annotation;
                if (!cookieValue.name().isEmpty()) {
                    return cookieValue.name();
                }
                if (!cookieValue.value().isEmpty()) {
                    return cookieValue.value();
                }
            }
        }
        return null;
    }
}
