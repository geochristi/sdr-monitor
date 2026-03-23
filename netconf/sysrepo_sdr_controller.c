#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <limits.h>
#include <sysrepo.h>
#include <sysrepo/values.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

#define CONTROL_FILE "/home/georgia/Desktop/SDR/control/phy_control.txt"
#define FALLBACK_CONTROL_FILE "/home/georgia/Desktop/SDR/phy_cotrol.txt"
#define CONTROL_FILE_MODE 0664
#define LOCK_FILE_MODE 0666
#define NOMINAL_CENTER_FREQUENCY_HZ 2400000000.0
#define FREQ_OFFSET_MIN_HZ (-1000000)
#define FREQ_OFFSET_MAX_HZ (1000000)

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

static int map_modulation_to_scheme(const char *raw, char *out, size_t out_sz)
{
    if (!raw || !out || out_sz == 0) {
        return -1;
    }

    if (strcasecmp(raw, "BPSK") == 0 || strcasecmp(raw, "2PSK") == 0) {
        return snprintf(out, out_sz, "0") >= 0 ? 0 : -1;
    }
    if (strcasecmp(raw, "QPSK") == 0 || strcasecmp(raw, "4PSK") == 0) {
        return snprintf(out, out_sz, "1") >= 0 ? 0 : -1;
    }
    if (strcasecmp(raw, "8PSK") == 0) {
        return snprintf(out, out_sz, "2") >= 0 ? 0 : -1;
    }
    if (strcasecmp(raw, "16QAM") == 0 || strcasecmp(raw, "QAM16") == 0) {
        return snprintf(out, out_sz, "3") >= 0 ? 0 : -1;
    }
    if (strcasecmp(raw, "64QAM") == 0 || strcasecmp(raw, "QAM64") == 0) {
        return snprintf(out, out_sz, "4") >= 0 ? 0 : -1;
    }

    return -1;
}

static int map_frequency_to_offset_hz(const char *raw_hz, char *out, size_t out_sz)
{
    char *end = NULL;
    double absolute_hz;
    double offset_hz;
    long long offset_i;

    if (!raw_hz || !out || out_sz == 0) {
        return -1;
    }

    errno = 0;
    absolute_hz = strtod(raw_hz, &end);
    if (errno != 0 || end == raw_hz) {
        return -1;
    }

    offset_hz = absolute_hz - NOMINAL_CENTER_FREQUENCY_HZ;

    if (offset_hz > (double)FREQ_OFFSET_MAX_HZ) {
        offset_hz = (double)FREQ_OFFSET_MAX_HZ;
    } else if (offset_hz < (double)FREQ_OFFSET_MIN_HZ) {
        offset_hz = (double)FREQ_OFFSET_MIN_HZ;
    }

    if (offset_hz >= 0.0) {
        offset_i = (long long)(offset_hz + 0.5);
    } else {
        offset_i = (long long)(offset_hz - 0.5);
    }
    return snprintf(out, out_sz, "%lld", offset_i) >= 0 ? 0 : -1;
}

static int key_matches_line(const char *line, const char *key)
{
    const char *eq;
    size_t key_len;

    if (!line || !key) {
        return 0;
    }

    eq = strchr(line, '=');
    if (!eq) {
        return 0;
    }

    key_len = (size_t)(eq - line);
    return strlen(key) == key_len && strncmp(line, key, key_len) == 0;
}

static int upsert_key_value_atomic(const char *path, const char *key, const char *value)
{
    FILE *in = NULL;
    FILE *out = NULL;
    char *line = NULL;
    size_t cap = 0;
    ssize_t read = 0;
    int replaced = 0;
    int ret = -1;
    char tmp_template[PATH_MAX];
    int tmp_fd = -1;

    if (snprintf(tmp_template, sizeof(tmp_template), "%s.tmpXXXXXX", path) >= (int)sizeof(tmp_template)) {
        return -1;
    }

    tmp_fd = mkstemp(tmp_template);
    if (tmp_fd < 0) {
        return -1;
    }

    out = fdopen(tmp_fd, "w");
    if (!out) {
        close(tmp_fd);
        unlink(tmp_template);
        return -1;
    }

    in = fopen(path, "r");
    if (in) {
        while ((read = getline(&line, &cap, in)) != -1) {
            if (key_matches_line(line, key)) {
                if (!replaced) {
                    fprintf(out, "%s=%s\n", key, value);
                    replaced = 1;
                }
                continue;
            }
            fputs(line, out);
            if (line[read - 1] != '\n') {
                fputc('\n', out);
            }
        }
        fclose(in);
        in = NULL;
    } else if (errno != ENOENT && errno != EACCES) {
        goto cleanup;
    }

    if (!replaced) {
        fprintf(out, "%s=%s\n", key, value);
    }

    fflush(out);
    fsync(fileno(out));
    fclose(out);
    out = NULL;

    if (rename(tmp_template, path) != 0) {
        unlink(tmp_template);
        goto cleanup;
    }

    (void)chmod(path, CONTROL_FILE_MODE);

    ret = 0;

cleanup:
    if (in) {
        fclose(in);
    }
    if (out) {
        fclose(out);
        unlink(tmp_template);
    }
    free(line);
    return ret;
}

static int write_control_param(const char *key, const char *value)
{
    char lock_path[PATH_MAX];
    char fallback_lock_path[PATH_MAX];
    int lock_fd = -1;
    int rc;

    if (snprintf(lock_path, sizeof(lock_path), "%s.lock", CONTROL_FILE) >= (int)sizeof(lock_path)) {
        return -1;
    }
    if (snprintf(fallback_lock_path, sizeof(fallback_lock_path), "%s.lock", FALLBACK_CONTROL_FILE) >= (int)sizeof(fallback_lock_path)) {
        return -1;
    }

    lock_fd = open(lock_path, O_CREAT | O_RDWR, LOCK_FILE_MODE);
    if (lock_fd < 0) {
        lock_fd = open(fallback_lock_path, O_CREAT | O_RDWR, LOCK_FILE_MODE);
        if (lock_fd < 0) {
            return -1;
        }
    }

    (void)fchmod(lock_fd, LOCK_FILE_MODE);

    if (flock(lock_fd, LOCK_EX) != 0) {
        close(lock_fd);
        return -1;
    }

    rc = upsert_key_value_atomic(CONTROL_FILE, key, value);
    if (rc != 0) {
        rc = upsert_key_value_atomic(FALLBACK_CONTROL_FILE, key, value);
    }

    flock(lock_fd, LOCK_UN);
    close(lock_fd);

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
                if (write_control_param(key, value_buf) != 0) {
                    fprintf(stderr, "Failed to write %s=%s to control file\n", key, value_buf);
                } else {
                    printf("WROTE %s=%s to control file\n", key, value_buf);
                    fflush(stdout);
                }
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
    return SR_ERR_OK;
}

int main() {
    sr_conn_ctx_t *conn = NULL;
    sr_session_ctx_t *session = NULL;
    sr_subscription_ctx_t *subscription = NULL;
    int rc;

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