#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { char name[32]; char value[32]; } Field;

static char *load(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END); long n = ftell(f); rewind(f);
    char *s = malloc((size_t)n + 1); fread(s, 1, (size_t)n, f); fclose(f); s[n] = 0;
    return s;
}

static int parse(const char *path, Field *out, int cap) {
    char *s = load(path), *p = s; int n = 0;
    while (n < cap && (p = strstr(p, "\"name\""))) {
        char *q = strchr(strchr(p, ':') + 1, '"');
        char *e = q ? strchr(q + 1, '"') : NULL;
        char *v = e ? strstr(e, "\"value_hex\"") : NULL;
        char *vq = v ? strchr(strchr(v, ':') + 1, '"') : NULL;
        char *ve = vq ? strchr(vq + 1, '"') : NULL;
        if (!q || !e || !vq || !ve) break;
        snprintf(out[n].name, sizeof out[n].name, "%.*s", (int)(e - q - 1), q + 1);
        snprintf(out[n].value, sizeof out[n].value, "%.*s", (int)(ve - vq - 1), vq + 1);
        n++; p = ve + 1;
    }
    free(s); return n;
}

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    Field a[32], b[32]; int na = parse(argv[1], a, 32), nb = parse(argv[2], b, 32), diff = 0;
    int n = na < nb ? na : nb;
    for (int i = 0; i < n; i++) {
        if (strcmp(a[i].name, b[i].name) || strcmp(a[i].value, b[i].value)) {
            printf("diff %s=%s %s=%s\n", a[i].name, a[i].value, b[i].name, b[i].value); diff++;
        }
    }
    diff += na > nb ? na - nb : nb - na;
    printf("summary original_fields=%d control_fields=%d differences=%d\n", na, nb, diff);
    return diff != 0;
}
