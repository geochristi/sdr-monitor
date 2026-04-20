#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sysrepo.h>
#include <sysrepo/values.h>
#include <zmq.h>
#if __has_include(<cjson/cJSON.h>)
#include <cjson/cJSON.h>
#elif __has_include(<cJSON.h>)
#include <cJSON.h>
#else
#error "cJSON header not found. Install libcjson-dev"
#endif

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

#define ZMQ_CONTROLLER_ADDR "tcp://127.0.0.1:5555"
#define ZMQ_TIMEOUT_MS 5000

/* ZMQ context (shared across callbacks) */
static void *zmq_context = NULL;

static const char *canonical_key_from_leaf(const char *leaf)
{
    if (!leaf) {
        return NULL;
    }

    if (strcmp(leaf, "packet_rate") == 0) {
        return "rate";
    }
    if (strcmp(leaf, "noise_level") == 0) {
        return "noise";
    }
    if (strcmp(leaf, "frequency_offset") == 0) {
        return "freq_offset";
    }

    if (strcmp(leaf, "noise") == 0 ||
        strcmp(leaf, "snr") == 0 ||
        strcmp(leaf, "rate") == 0 ||
        strcmp(leaf, "freq_offset") == 0 ||
        strcmp(leaf, "mod_scheme") == 0 ||
        strcmp(leaf, "ber_inject") == 0) {
        return leaf;
    }

    return NULL;
}

static const char *leaf_from_xpath(const char *xpath)
{
    const char *slash;
    static char leaf[128];
    size_t i = 0;

    if (!xpath) {
        return NULL;
    }

    slash = strrchr(xpath, '/');
    if (!slash || !*(slash + 1)) {
        return NULL;
    }

    slash++;
    while (*slash && *slash != '[' && *slash != '/' && i < sizeof(leaf) - 1) {
        leaf[i++] = *slash++;
    }
    leaf[i] = '\0';

    if (i == 0) {
        return NULL;
    }

    return leaf;
}

static int format_sr_value(const sr_val_t *val, char *out, size_t out_sz)
{
    if (!val || !out || out_sz == 0) {
        return -1;
    }

    switch (val->type) {
    case SR_STRING_T:
        return snprintf(out, out_sz, "%s", val->data.string_val ? val->data.string_val : "") >= 0 ? 0 : -1;
    case SR_UINT32_T:
        return snprintf(out, out_sz, "%u", val->data.uint32_val) >= 0 ? 0 : -1;
    case SR_DECIMAL64_T:
        return snprintf(out, out_sz, "%.6f", val->data.decimal64_val) >= 0 ? 0 : -1;
    case SR_INT32_T:
        return snprintf(out, out_sz, "%d", val->data.int32_val) >= 0 ? 0 : -1;
    case SR_BOOL_T:
        return snprintf(out, out_sz, "%d", val->data.bool_val ? 1 : 0) >= 0 ? 0 : -1;
    default:
        return -1;
    }
}

/*
 * Send a single SET_CONFIG message with all changed parameters batched.
 * config_obj: cJSON object mapping canonical key -> value (number or string).
 */
static int zmq_set_config(cJSON *config_obj, const char *source)
{
    void *socket = NULL;
    cJSON *request = NULL;
    cJSON *response = NULL;
    char *request_str = NULL;
    char buffer[4096];
    int size;
    int rc = -1;

    if (!zmq_context || !config_obj) {
        fprintf(stderr, "Invalid arguments to zmq_set_config\n");
        return -1;
    }

    socket = zmq_socket(zmq_context, ZMQ_REQ);
    if (!socket) {
        fprintf(stderr, "Failed to create ZMQ socket: %s\n", zmq_strerror(zmq_errno()));
        return -1;
    }

    {
        int timeout = ZMQ_TIMEOUT_MS;
        int linger = 0;
        zmq_setsockopt(socket, ZMQ_RCVTIMEO, &timeout, sizeof(timeout));
        zmq_setsockopt(socket, ZMQ_LINGER, &linger, sizeof(linger));
    }

    if (zmq_connect(socket, ZMQ_CONTROLLER_ADDR) != 0) {
        fprintf(stderr, "Failed to connect to ZMQ controller: %s\n", zmq_strerror(zmq_errno()));
        zmq_close(socket);
        return -1;
    }

    request = cJSON_CreateObject();
    if (!request) {
        fprintf(stderr, "Failed to create JSON request\n");
        zmq_close(socket);
        return -1;
    }

    cJSON_AddStringToObject(request, "op", "SET_CONFIG");
    cJSON_AddStringToObject(request, "source", source ? source : "netconf");
    /* config_obj is transferred into the request; do NOT free it separately */
    cJSON_AddItemToObject(request, "config", config_obj);

    request_str = cJSON_PrintUnformatted(request);
    if (!request_str) {
        fprintf(stderr, "Failed to serialize JSON request\n");
        goto cleanup;
    }

    if (zmq_send(socket, request_str, strlen(request_str), 0) < 0) {
        fprintf(stderr, "[ZMQ] Failed to send request: %s\n", zmq_strerror(zmq_errno()));
        goto cleanup;
    }

    size = zmq_recv(socket, buffer, sizeof(buffer) - 1, 0);
    if (size < 0) {
        if (zmq_errno() == EAGAIN) {
            fprintf(stderr, "[ZMQ] Timeout waiting for response\n");
        } else {
            fprintf(stderr, "[ZMQ] Failed to receive response: %s\n", zmq_strerror(zmq_errno()));
        }
        goto cleanup;
    }

    buffer[size] = '\0';
    response = cJSON_Parse(buffer);
    if (!response) {
        fprintf(stderr, "[ZMQ] Failed to parse response JSON\n");
        goto cleanup;
    }

    {
        cJSON *status = cJSON_GetObjectItemCaseSensitive(response, "status");
        if (cJSON_IsString(status) && status->valuestring && strcmp(status->valuestring, "OK") == 0) {
            rc = 0;
        } else {
            cJSON *error_item = cJSON_GetObjectItemCaseSensitive(response, "error");
            fprintf(stderr, "[ZMQ] Controller error: %s\n",
                    cJSON_IsString(error_item) && error_item->valuestring ? error_item->valuestring : "Unknown");
        }
    }

cleanup:
    if (response) {
        cJSON_Delete(response);
    }
    /* request owns config_obj via cJSON_AddItemToObject, so deleting request frees both */
    if (request) {
        cJSON_Delete(request);
    }
    if (request_str) {
        free(request_str);
    }
    if (socket) {
        zmq_close(socket);
    }

    return rc;
}

static int module_change_cb(sr_session_ctx_t *session,
                            uint32_t sub_id,
                            const char *module_name,
                            const char *xpath,
                            sr_event_t event,
                            uint32_t request_id,
                            void *private_data)
{
    (void)sub_id;
    (void)module_name;
    (void)xpath;
    (void)request_id;
    (void)private_data;

    printf(">>> CALLBACK EVENT = %d\n", event);
    fflush(stdout);

    if (event != SR_EV_CHANGE && event != SR_EV_DONE)
        return SR_ERR_OK;

    sr_change_iter_t *it = NULL;
    sr_change_oper_t oper;
    sr_val_t *old_val = NULL;
    sr_val_t *new_val = NULL;
    int rc;

    printf("\n=== SDR CONFIG CHANGES ===\n");

    rc = sr_get_changes_iter(session, "/sdr-phy:*//.", &it);
    if (rc != SR_ERR_OK || !it) {
        fprintf(stderr, "Failed to get change iterator: rc=%d\n", rc);
        return SR_ERR_OK;
    }

    /* Collect all changed params into a single cJSON object */
    cJSON *config = cJSON_CreateObject();
    if (!config) {
        fprintf(stderr, "Failed to allocate config JSON object\n");
        sr_free_change_iter(it);
        return SR_ERR_OK;
    }

    while (sr_get_change_next(session, it, &oper, &old_val, &new_val) == SR_ERR_OK) {
        if (new_val) {
            const char *leaf = leaf_from_xpath(new_val->xpath);
            const char *key = canonical_key_from_leaf(leaf);
            char value_buf[128];

            printf("%s = ", new_val->xpath);

            switch (new_val->type) {
                case SR_STRING_T:
                    printf("%s\n", new_val->data.string_val);
                    break;
                case SR_UINT32_T:
                    printf("%u\n", new_val->data.uint32_val);
                    break;
                case SR_DECIMAL64_T:
                    printf("%lf\n", new_val->data.decimal64_val);
                    break;
                default:
                    printf("Other type\n");
            }

            if (key && format_sr_value(new_val, value_buf, sizeof(value_buf)) == 0) {
                /* Add to config batch, auto-detecting numeric vs string */
                char *endptr = NULL;
                long int_val = strtol(value_buf, &endptr, 10);
                if (endptr && *endptr == '\0') {
                    cJSON_AddNumberToObject(config, key, (double)int_val);
                } else {
                    double float_val = strtod(value_buf, &endptr);
                    if (endptr && *endptr == '\0') {
                        cJSON_AddNumberToObject(config, key, float_val);
                    } else {
                        cJSON_AddStringToObject(config, key, value_buf);
                    }
                }
                printf("  queued: %s=%s\n", key, value_buf);
            } else if (!key) {
                fprintf(stderr, "Ignoring unmapped leaf: %s\n", new_val->xpath);
            }
        }

        if (old_val) {
            sr_free_val(old_val);
            old_val = NULL;
        }
        if (new_val) {
            sr_free_val(new_val);
            new_val = NULL;
        }
    }

    if (old_val) {
        sr_free_val(old_val);
    }
    if (new_val) {
        sr_free_val(new_val);
    }

    sr_free_change_iter(it);

    /* Send batch only if there is at least one param */
    int param_count = cJSON_GetArraySize(config);
    if (param_count > 0) {
        /* config ownership transferred to zmq_set_config; it will be freed there */
        if (zmq_set_config(config, "netconf") != 0) {
            fprintf(stderr, "Failed to send SET_CONFIG via ZMQ\n");
        } else {
            printf("ZMQ SET_CONFIG sent (%d param(s))\n", param_count);
            fflush(stdout);
        }
    } else {
        cJSON_Delete(config);
    }

    return SR_ERR_OK;
}

int main() {
    sr_conn_ctx_t *conn = NULL;
    sr_session_ctx_t *session = NULL;
    sr_subscription_ctx_t *subscription = NULL;
    int rc;

    zmq_context = zmq_ctx_new();
    if (!zmq_context) {
        fprintf(stderr, "Failed to initialize ZMQ context\n");
        return 1;
    }

    printf("Connecting to sysrepo...\n");
    rc = sr_connect(0, &conn);
    if (rc != SR_ERR_OK) {
        fprintf(stderr, "sr_connect failed: rc=%d\n", rc);
        return 1;
    }

    printf("Starting session...\n");
    rc = sr_session_start(conn, SR_DS_RUNNING, &session);
    if (rc != SR_ERR_OK) {
        fprintf(stderr, "sr_session_start failed: rc=%d\n", rc);
        sr_disconnect(conn);
        return 1;
    }

    printf("Subscribing to module changes...\n");
    rc = sr_module_change_subscribe(session,
                                    "sdr-phy",
                                    NULL,
                                    module_change_cb,
                                    NULL,
                                    0,
                                    SR_SUBSCR_DEFAULT,
                                    &subscription);
    if (rc != SR_ERR_OK) {
        fprintf(stderr, "sr_module_change_subscribe failed: rc=%d\n", rc);
        sr_session_stop(session);
        sr_disconnect(conn);
        return 1;
    }

    printf("Waiting for changes...\n");

    while (1) {
        sleep(10);
    }

    return 0;
}