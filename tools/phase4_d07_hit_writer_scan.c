#define _DEFAULT_SOURCE
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

typedef struct { char **line; size_t count; } Lines;

static int ends_s(const char *name) {
    size_t n = strlen(name); return n >= 2 && !strcmp(name + n - 2, ".s");
}

static Lines read_lines(const char *path) {
    Lines out = {0}; FILE *f = fopen(path, "r"); if (!f) return out;
    size_t cap = 128; out.line = malloc(cap * sizeof *out.line);
    char *line = NULL; size_t size = 0; ssize_t got;
    while ((got = getline(&line, &size, f)) >= 0) {
        if (out.count == cap) { cap *= 2; out.line = realloc(out.line, cap * sizeof *out.line); }
        out.line[out.count++] = strdup(line);
    }
    free(line); fclose(f); return out;
}

static void free_lines(Lines *lines) {
    for (size_t i = 0; i < lines->count; i++) free(lines->line[i]);
    free(lines->line);
}

static int is_set_1000(const char *line) {
    return strstr(line, "ori ") && (strstr(line, "0x1000") || strstr(line, ", 1000"));
}

static int is_store_flags(const char *line) {
    return strstr(line, "sh ") && (strstr(line, "0x5c(") || strstr(line, "5c00"));
}

static void scan_file(const char *path) {
    Lines lines = read_lines(path);
    for (size_t i = 0; i < lines.count; i++) {
        if (!is_set_1000(lines.line[i])) continue;
        size_t begin = i > 16 ? i - 16 : 0;
        size_t end = i + 17 < lines.count ? i + 17 : lines.count;
        for (size_t j = begin; j < end; j++) {
            if (!is_store_flags(lines.line[j])) continue;
            printf("candidate file=%s ori_line=%zu store_line=%zu\n", path, i + 1, j + 1);
            printf("  ORI: %s", lines.line[i]);
            printf("  STORE: %s", lines.line[j]);
        }
    }
    free_lines(&lines);
}

static void walk(const char *path) {
    struct stat st; if (lstat(path, &st)) return;
    if (S_ISREG(st.st_mode)) { if (ends_s(path)) scan_file(path); return; }
    if (!S_ISDIR(st.st_mode)) return;
    DIR *dir = opendir(path); if (!dir) return;
    struct dirent *entry;
    while ((entry = readdir(dir))) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        size_t n = strlen(path) + strlen(entry->d_name) + 2;
        char *child = malloc(n); snprintf(child, n, "%s/%s", path, entry->d_name);
        walk(child); free(child);
    }
    closedir(dir);
}

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: %s asm_root\n", argv[0]); return 2; }
    walk(argv[1]); return 0;
}
