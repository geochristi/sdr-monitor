/*
 * zmq_client.h
 * Simple C client library for communicating with the ZMQ controller daemon
 */

#ifndef ZMQ_CLIENT_H
#define ZMQ_CLIENT_H

#include <zmq.h>
#include <cJSON.h>

#define DEFAULT_REQ_REP_ADDR "tcp://127.0.0.1:5555"
#define DEFAULT_TIMEOUT_MS 5000

typedef struct {
    void *context;
    void *socket;
} zmq_controller_client_t;

/**
 * Connect to the ZMQ controller and create a client handle.
 * 
 * @param addr Address of the controller's REQ/REP socket (or NULL for default)
 * @param timeout_ms Timeout in milliseconds for operations
 * @return Allocated client handle, or NULL on failure
 */
zmq_controller_client_t *zmq_client_new(const char *addr, int timeout_ms);

/**
 * Close the client connection and free resources.
 * 
 * @param client Client handle to close (can be NULL)
 */
void zmq_client_free(zmq_controller_client_t *client);

/**
 * Get a single parameter value (integer or float).
 * 
 * @param client Client handle
 * @param param_name Parameter name (e.g., "freq_offset", "mod_scheme")
 * @param out_json Pointer to receive the full response JSON (caller must free with cJSON_Delete)
 * @return 0 on success, -1 on error
 */
int zmq_client_get_param(zmq_controller_client_t *client, const char *param_name, cJSON **out_json);

/**
 * Set a single parameter value.
 * 
 * @param client Client handle
 * @param param_name Parameter name
 * @param value Value to set (can be integer or float as cJSON object)
 * @param source Source identifier for logging (e.g., "netconf", "snmp")
 * @param out_json Pointer to receive the full response JSON (caller must free with cJSON_Delete)
 * @return 0 on success, -1 on error
 */
int zmq_client_set_param(zmq_controller_client_t *client, const char *param_name, 
                         const char *value, const char *source, cJSON **out_json);

/**
 * Get all parameter values.
 * 
 * @param client Client handle
 * @param out_json Pointer to receive the full response JSON with params dict (caller must free with cJSON_Delete)
 * @return 0 on success, -1 on error
 */
int zmq_client_get_all(zmq_controller_client_t *client, cJSON **out_json);

/**
 * Send a raw JSON request and receive response.
 * 
 * @param client Client handle
 * @param request cJSON object to send (will be serialized to string)
 * @param out_response Pointer to receive response JSON (caller must free with cJSON_Delete)
 * @return 0 on success, -1 on error or timeout
 */
int zmq_client_request(zmq_controller_client_t *client, cJSON *request, cJSON **out_response);

#endif
