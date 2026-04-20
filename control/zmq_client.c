/*
 * zmq_client.c
 * Implementation of ZMQ controller client library
 */

#include "zmq_client.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

zmq_controller_client_t *zmq_client_new(const char *addr, int timeout_ms)
{
    if (!addr) {
        addr = DEFAULT_REQ_REP_ADDR;
    }
    if (timeout_ms <= 0) {
        timeout_ms = DEFAULT_TIMEOUT_MS;
    }

    zmq_controller_client_t *client = (zmq_controller_client_t *)malloc(sizeof(*client));
    if (!client) {
        perror("malloc");
        return NULL;
    }

    // Create context
    client->context = zmq_ctx_new();
    if (!client->context) {
        free(client);
        return NULL;
    }

    // Create REQ socket
    client->socket = zmq_socket(client->context, ZMQ_REQ);
    if (!client->socket) {
        zmq_ctx_destroy(client->context);
        free(client);
        return NULL;
    }

    // Set timeout
    zmq_setsockopt(client->socket, ZMQ_RCVTIMEO, &timeout_ms, sizeof(timeout_ms));
    zmq_setsockopt(client->socket, ZMQ_LINGER, (int[]){0}, sizeof(int));

    // Connect
    if (zmq_connect(client->socket, addr) != 0) {
        zmq_close(client->socket);
        zmq_ctx_destroy(client->context);
        free(client);
        return NULL;
    }

    return client;
}

void zmq_client_free(zmq_controller_client_t *client)
{
    if (!client) {
        return;
    }

    if (client->socket) {
        zmq_close(client->socket);
    }
    if (client->context) {
        zmq_ctx_destroy(client->context);
    }
    free(client);
}

int zmq_client_request(zmq_controller_client_t *client, cJSON *request, cJSON **out_response)
{
    if (!client || !request || !out_response) {
        return -1;
    }

    // Serialize request to JSON string
    char *request_str = cJSON_Print(request);
    if (!request_str) {
        fprintf(stderr, "Failed to serialize request JSON\n");
        return -1;
    }

    // Send request
    if (zmq_send(client->socket, request_str, strlen(request_str), 0) < 0) {
        fprintf(stderr, "Failed to send ZMQ request: %s\n", zmq_strerror(zmq_errno()));
        free(request_str);
        return -1;
    }

    // Receive response
    char buffer[4096];
    int size = zmq_recv(client->socket, buffer, sizeof(buffer) - 1, 0);
    free(request_str);

    if (size < 0) {
        if (zmq_errno() == EAGAIN) {
            fprintf(stderr, "ZMQ request timeout\n");
        } else {
            fprintf(stderr, "Failed to receive ZMQ response: %s\n", zmq_strerror(zmq_errno()));
        }
        return -1;
    }

    buffer[size] = '\0';

    // Parse response JSON
    cJSON *response = cJSON_Parse(buffer);
    if (!response) {
        fprintf(stderr, "Failed to parse response JSON: %s\n", buffer);
        return -1;
    }

    *out_response = response;
    return 0;
}

int zmq_client_get_param(zmq_controller_client_t *client, const char *param_name, cJSON **out_json)
{
    if (!client || !param_name || !out_json) {
        return -1;
    }

    // Build GET request
    cJSON *request = cJSON_CreateObject();
    cJSON_AddStringToObject(request, "op", "GET");
    cJSON_AddStringToObject(request, "param", param_name);

    // Send and receive
    cJSON *response = NULL;
    int result = zmq_client_request(client, request, &response);
    cJSON_Delete(request);

    if (result != 0) {
        return -1;
    }

    *out_json = response;
    return 0;
}

int zmq_client_set_param(zmq_controller_client_t *client, const char *param_name,
                         const char *value, const char *source, cJSON **out_json)
{
    if (!client || !param_name || !value || !out_json) {
        return -1;
    }

    // Build SET request
    cJSON *request = cJSON_CreateObject();
    cJSON_AddStringToObject(request, "op", "SET");
    cJSON_AddStringToObject(request, "param", param_name);
    
    // Try to parse value as number first, then as string
    cJSON *val_obj = NULL;
    char *endptr;
    long int_val = strtol(value, &endptr, 10);
    if (*endptr == '\0') {
        // Successfully parsed as integer
        val_obj = cJSON_CreateNumber(int_val);
    } else {
        // Try as float
        double float_val = strtod(value, &endptr);
        if (*endptr == '\0') {
            val_obj = cJSON_CreateNumber(float_val);
        } else {
            // Keep as string
            val_obj = cJSON_CreateString(value);
        }
    }
    
    cJSON_AddItemToObject(request, "value", val_obj);
    
    if (source) {
        cJSON_AddStringToObject(request, "source", source);
    } else {
        cJSON_AddStringToObject(request, "source", "zmq-c-client");
    }

    // Send and receive
    cJSON *response = NULL;
    int result = zmq_client_request(client, request, &response);
    cJSON_Delete(request);

    if (result != 0) {
        return -1;
    }

    *out_json = response;
    return 0;
}

int zmq_client_get_all(zmq_controller_client_t *client, cJSON **out_json)
{
    if (!client || !out_json) {
        return -1;
    }

    // Build GET_ALL request
    cJSON *request = cJSON_CreateObject();
    cJSON_AddStringToObject(request, "op", "GET_ALL");

    // Send and receive
    cJSON *response = NULL;
    int result = zmq_client_request(client, request, &response);
    cJSON_Delete(request);

    if (result != 0) {
        return -1;
    }

    *out_json = response;
    return 0;
}
