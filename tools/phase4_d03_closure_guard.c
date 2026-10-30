#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *read_text(const char *path)
{
    FILE *file = fopen(path, "rb");
    long size;
    char *text;

    if (file == NULL)
        return NULL;
    if (fseek(file, 0, SEEK_END) != 0 || (size = ftell(file)) < 0 || fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return NULL;
    }
    text = malloc((size_t)size + 1);
    if (text == NULL || fread(text, 1, (size_t)size, file) != (size_t)size) {
        free(text);
        fclose(file);
        return NULL;
    }
    text[size] = '\0';
    fclose(file);
    return text;
}

static char *compact_json(const char *text)
{
    size_t length = strlen(text);
    char *compact = malloc(length + 1);
    size_t out = 0;
    int in_string = 0;
    int escaped = 0;

    if (compact == NULL)
        return NULL;
    for (size_t i = 0; i < length; i++) {
        char c = text[i];
        if (!in_string && (c == ' ' || c == '\t' || c == '\r' || c == '\n'))
            continue;
        compact[out++] = c;
        if (in_string && c == '\\' && !escaped) {
            escaped = 1;
            continue;
        }
        if (c == '"' && !escaped)
            in_string = !in_string;
        escaped = 0;
    }
    compact[out] = '\0';
    return compact;
}

static void require_token(const char *document, const char *token, const char *message)
{
    if (strstr(document, token) == NULL) {
        fprintf(stderr, "phase4_d03_closure_guard: %s (missing %s)\n", message, token);
        exit(1);
    }
}

static void require_any(const char *document, const char *first, const char *second,
                        const char *message)
{
    if (strstr(document, first) == NULL && strstr(document, second) == NULL) {
        fprintf(stderr, "phase4_d03_closure_guard: %s\n", message);
        exit(1);
    }
}

int main(int argc, char **argv)
{
    char *static_raw;
    char *capsule_raw;
    char *runtime_raw;
    char *static_json;
    char *capsule_json;
    char *runtime_json;

    if (argc != 4) {
        fprintf(stderr, "usage: %s STATIC.json CAPSULE.json RUNTIME.json\n", argv[0]);
        return 2;
    }
    static_raw = read_text(argv[1]);
    capsule_raw = read_text(argv[2]);
    runtime_raw = read_text(argv[3]);
    if (static_raw == NULL || capsule_raw == NULL || runtime_raw == NULL) {
        fprintf(stderr, "phase4_d03_closure_guard: cannot read an input artifact\n");
        return 1;
    }
    static_json = compact_json(static_raw);
    capsule_json = compact_json(capsule_raw);
    runtime_json = compact_json(runtime_raw);
    if (static_json == NULL || capsule_json == NULL || runtime_json == NULL)
        return 1;

    require_token(static_json, "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20",
                  "static result is not bound to the pristine executable");
    require_any(static_json, "\"anchors_checked\":56", "\"anchor_checks\":56",
                "static result does not contain the exact 56-anchor count");
    require_token(static_json, "0x800496B0", "static caller 0x800496B0 disappeared");
    require_token(static_json, "0x80049740", "static caller 0x80049740 disappeared");
    require_token(static_json, "0x80049868", "static caller 0x80049868 disappeared");
    require_token(static_json, "0x8004B4A0", "static caller 0x8004B4A0 disappeared");
    require_token(static_json, "0x80058A48", "static caller 0x80058A48 disappeared");
    require_token(static_json, "0x8005C9F8", "static caller 0x8005C9F8 disappeared");

    require_token(capsule_json, "2692", "capsule boundary total disappeared");
    require_token(capsule_json, "8076", "capsule hash-check total disappeared");
    require_any(capsule_json, "\"hash_mismatches\":0", "\"mismatches\":0",
                "capsule hash integrity is no longer clean");
    require_token(capsule_json, "B07", "heal control disappeared from capsule result");
    require_token(capsule_json, "D08", "fly positive control disappeared from capsule result");
    require_token(capsule_json, "D11", "grub/mite positive controls disappeared from capsule result");
    require_token(capsule_json, "45", "45-tick contact timer evidence disappeared");

    require_token(runtime_json, "\"schema\":\"abl-phase4-d03-runtime-v1\"",
                  "runtime artifact schema mismatch");
    require_token(runtime_json, "\"guard_passed\":true", "runtime semantic guard did not pass");
    require_token(runtime_json, "\"intervention\":\"none\"", "runtime control was not native");
    require_token(runtime_json, "\"first_positive_frame\":65268", "initial positive control changed");
    require_token(runtime_json, "\"first_timer_expiry_frame\":65358", "timer expiry control changed");
    require_token(runtime_json, "\"post_expiry_positive_frame\":65372", "post-expiry control changed");
    require_token(runtime_json, "\"timer_at_entry\":25", "positive-timer admission at 25 disappeared");
    require_token(runtime_json, "\"timer_at_entry\":14", "positive-timer admission at 14 disappeared");
    require_token(runtime_json, "\"health_store\":false", "suppressed health-store control disappeared");

    puts("D03 closure guard: PASS (56 anchors, 6 callers, capsule integrity, native iframe suppression, post-expiry re-hit)");
    free(static_raw);
    free(capsule_raw);
    free(runtime_raw);
    free(static_json);
    free(capsule_json);
    free(runtime_json);
    return 0;
}
