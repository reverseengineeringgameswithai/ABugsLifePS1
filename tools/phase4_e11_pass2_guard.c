#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct fixture {
    int scene;
    const char *path;
    int expected_max_index;
};

static uint16_t rd16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int spans(size_t off, size_t length, size_t size) {
    return off <= size && length <= size - off;
}

static uint8_t *load_file(const char *path, size_t *size_out) {
    FILE *file = fopen(path, "rb");
    uint8_t *data;
    long length;

    if (!file) {
        fprintf(stderr, "%s: %s\n", path, strerror(errno));
        return NULL;
    }
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET) != 0) {
        fprintf(stderr, "%s: cannot determine file length\n", path);
        fclose(file);
        return NULL;
    }
    data = malloc((size_t)length);
    if (!data || fread(data, 1, (size_t)length, file) != (size_t)length) {
        fprintf(stderr, "%s: cannot read file\n", path);
        free(data);
        fclose(file);
        return NULL;
    }
    fclose(file);
    *size_out = (size_t)length;
    return data;
}

static int inspect(const struct fixture *fixture) {
    uint8_t *data;
    uint32_t record_count;
    uint32_t geometry_words;
    size_t size;
    size_t offset = 4;
    size_t trail;
    size_t pass1_count = 0;
    size_t pass2;
    size_t nonnull = 0;
    int32_t max_index;
    int failed = 0;

    data = load_file(fixture->path, &size);
    if (!data)
        return 1;
    if (!spans(0, 4, size))
        goto malformed;

    record_count = rd32(data);
    for (uint32_t i = 0; i < record_count; ++i) {
        uint16_t count;
        int16_t type;
        size_t stride;

        if (!spans(offset, 4, size))
            goto malformed;
        count = rd16(data + offset);
        type = (int16_t)rd16(data + offset + 2);
        if (type < 0)
            stride = ((((size_t)count * 3 + 1) >> 1) << 2) + 0x10;
        else if (type == 0x3f)
            stride = (size_t)count * 0x10 + 4;
        else
            stride = (size_t)count * 0x0c + 4;
        if (!stride || !spans(offset, stride, size))
            goto malformed;
        offset += stride;
    }

    if (!spans(offset, 4, size))
        goto malformed;
    geometry_words = rd32(data + offset);
    if ((uint64_t)offset + 4 + ((uint64_t)geometry_words << 7) > size)
        goto malformed;
    trail = offset + 4 + ((size_t)geometry_words << 7);

    for (;;) {
        size_t flags = trail + pass1_count * 0x14 + 0x0e;
        if (!spans(flags, 2, size))
            goto malformed;
        if ((int16_t)rd16(data + flags) < 0)
            break;
        if (++pass1_count > size / 0x14)
            goto malformed;
    }

    pass2 = trail + (pass1_count + 1) * 0x14;
    if (!spans(pass2, 4, size))
        goto malformed;
    max_index = (int32_t)rd32(data + pass2);
    if (max_index < -1 ||
        (max_index >= 0 &&
         !spans(pass2 + 4, ((size_t)max_index + 1) * 4, size)))
        goto malformed;

    if (max_index >= 0) {
        for (int32_t i = 0; i <= max_index; ++i) {
            uint32_t object = rd32(data + pass2 + 4 + (size_t)i * 4);
            if (object != 0) {
                ++nonnull;
                if (!spans(object, 0x14, size)) {
                    fprintf(stderr,
                            "scene %d slot %d has out-of-range object 0x%08x\n",
                            fixture->scene, i, object);
                    failed = 1;
                }
            }
        }
    }

    if (max_index != fixture->expected_max_index) {
        fprintf(stderr, "scene %d expected max index %d, found %d\n",
                fixture->scene, fixture->expected_max_index, max_index);
        failed = 1;
    }
    if (nonnull != (max_index < 0 ? 0U : (size_t)max_index + 1)) {
        fprintf(stderr, "scene %d has %zu non-null slots for max index %d\n",
                fixture->scene, nonnull, max_index);
        failed = 1;
    }

    printf("scene=%d max_index=%d slots=%d nonnull=%zu pass1=%zu pass2=0x%zx %s\n",
           fixture->scene, max_index, max_index < 0 ? 0 : max_index + 1,
           nonnull, pass1_count, pass2, failed ? "FAIL" : "PASS");
    free(data);
    return failed;

malformed:
    fprintf(stderr, "scene %d malformed while locating pass2 in %s\n",
            fixture->scene, fixture->path);
    free(data);
    return 1;
}

int main(void) {
    static const struct fixture fixtures[] = {
        {1, "REBUILD/files/LEVEL01/LEVEL.DAT", -1},
        {2, "REBUILD/files/LEVEL02/LEVEL.DAT", -1},
        {3, "REBUILD/files/LEVEL03/LEVEL.DAT", 28},
        {4, "REBUILD/files/LEVEL04/LEVEL.DAT", 5},
        {5, "REBUILD/files/LEVEL05/LEVEL.DAT", -1},
        {6, "REBUILD/files/LEVEL06/LEVEL.DAT", -1},
        {7, "REBUILD/files/LEVEL07/LEVEL.DAT", -1},
        {8, "REBUILD/files/LEVEL08/LEVEL.DAT", -1},
        {9, "REBUILD/files/LEVEL09/LEVEL.DAT", -1},
        {10, "REBUILD/files/LEVEL10/LEVEL.DAT", -1},
        {11, "REBUILD/files/LEVEL01/LEVEL1.DAT", -1},
        {12, "REBUILD/files/LEVEL02/LEVEL1.DAT", -1},
        {13, "REBUILD/files/LEVEL03/LEVEL1.DAT", -1},
        {14, "REBUILD/files/LEVEL04/LEVEL1.DAT", 9},
        {15, "REBUILD/files/LEVEL05/LEVEL1.DAT", 1},
    };
    int failed = 0;

    for (size_t i = 0; i < sizeof(fixtures) / sizeof(fixtures[0]); ++i)
        failed |= inspect(&fixtures[i]);
    return failed ? EXIT_FAILURE : EXIT_SUCCESS;
}
