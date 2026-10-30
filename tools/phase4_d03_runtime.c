#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { MAX_EVENTS = 20000 };

typedef struct {
    uint64_t frame;
    uint64_t cycle;
    uint32_t address;
    uint32_t pc;
    int64_t old_value;
    int64_t new_value;
} AccessEvent;

typedef struct {
    uint64_t frame;
    uint64_t cycle;
    uint32_t pc;
} ExecEvent;

typedef struct {
    uint64_t frame;
    uint64_t cycle;
    int timer_at_entry;
    int health_at_entry;
    int reached_branch;
    int reached_health_store;
    int wrote_health;
    int reset_timer;
} Admission;

static void die(const char *message)
{
    fprintf(stderr, "phase4_d03_runtime: %s\n", message);
    exit(1);
}

static uint32_t parse_hex32(const char *text)
{
    char *end = NULL;
    unsigned long value;

    errno = 0;
    value = strtoul(text, &end, 0);
    if (errno != 0 || end == text || *end != '\0' || value > UINT32_MAX)
        die("invalid 32-bit hexadecimal value in input");
    return (uint32_t)value;
}

static size_t read_access_events(const char *path, AccessEvent *events)
{
    FILE *file = fopen(path, "r");
    size_t count = 0;
    char address[32];
    char pc[32];

    if (file == NULL)
        die("cannot open access-event TSV");
    while (count < MAX_EVENTS &&
           fscanf(file, "%" SCNu64 "\t%" SCNu64 "\t%31s\t%31s\t%" SCNd64 "\t%" SCNd64,
                  &events[count].frame, &events[count].cycle, address, pc,
                  &events[count].old_value, &events[count].new_value) == 6) {
        events[count].address = parse_hex32(address);
        events[count].pc = parse_hex32(pc);
        count++;
    }
    if (!feof(file))
        die(count == MAX_EVENTS ? "access-event cap reached" : "malformed access-event TSV");
    fclose(file);
    return count;
}

static size_t read_exec_events(const char *path, ExecEvent *events)
{
    FILE *file = fopen(path, "r");
    size_t count = 0;
    char pc[32];

    if (file == NULL)
        die("cannot open execution-event TSV");
    while (count < MAX_EVENTS &&
           fscanf(file, "%" SCNu64 "\t%" SCNu64 "\t%31s",
                  &events[count].frame, &events[count].cycle, pc) == 3) {
        events[count].pc = parse_hex32(pc);
        count++;
    }
    if (!feof(file))
        die(count == MAX_EVENTS ? "execution-event cap reached" : "malformed execution-event TSV");
    fclose(file);
    return count;
}

static int exec_between(const ExecEvent *events, size_t count, uint32_t pc,
                        uint64_t first_cycle, uint64_t limit_cycle)
{
    for (size_t i = 0; i < count; i++) {
        if (events[i].cycle >= first_cycle && events[i].cycle < limit_cycle && events[i].pc == pc)
            return 1;
    }
    return 0;
}

static int access_between(const AccessEvent *events, size_t count, uint32_t address,
                          int64_t new_value, uint64_t first_cycle, uint64_t limit_cycle)
{
    for (size_t i = 0; i < count; i++) {
        if (events[i].cycle >= first_cycle && events[i].cycle < limit_cycle &&
            events[i].address == address && events[i].new_value == new_value)
            return 1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    static AccessEvent access_events[MAX_EVENTS];
    static ExecEvent exec_events[MAX_EVENTS];
    static Admission admissions[MAX_EVENTS];
    const uint32_t timer_address = UINT32_C(0x800a6592);
    const uint32_t health_address = UINT32_C(0x800a6594);
    const uint32_t handler_pc = UINT32_C(0x8004a700);
    const uint32_t branch_pc = UINT32_C(0x8004a790);
    const uint32_t health_store_pc = UINT32_C(0x8004a888);
    size_t access_count;
    size_t exec_count;
    size_t admission_count = 0;
    size_t suppressed_count = 0;
    size_t positive_count = 0;
    int timer = 0;
    int health = 4;
    size_t access_cursor = 0;
    uint64_t first_expiry_frame = 0;
    uint64_t first_positive_frame = 0;
    uint64_t second_positive_frame = 0;

    if (argc != 3) {
        fprintf(stderr, "usage: %s ACCESS.tsv EXEC.tsv\n", argv[0]);
        return 2;
    }
    access_count = read_access_events(argv[1], access_events);
    exec_count = read_exec_events(argv[2], exec_events);

    for (size_t i = 0; i < exec_count; i++) {
        uint64_t limit_cycle;
        Admission *admission;

        if (exec_events[i].pc != handler_pc)
            continue;
        if (admission_count == MAX_EVENTS)
            die("admission cap reached");
        while (access_cursor < access_count && access_events[access_cursor].cycle < exec_events[i].cycle) {
            if (access_events[access_cursor].address == timer_address)
                timer = (int)access_events[access_cursor].new_value;
            else if (access_events[access_cursor].address == health_address)
                health = (int)access_events[access_cursor].new_value;
            access_cursor++;
        }
        limit_cycle = UINT64_MAX;
        for (size_t j = i + 1; j < exec_count; j++) {
            if (exec_events[j].pc == handler_pc) {
                limit_cycle = exec_events[j].cycle;
                break;
            }
        }
        admission = &admissions[admission_count++];
        admission->frame = exec_events[i].frame;
        admission->cycle = exec_events[i].cycle;
        admission->timer_at_entry = timer;
        admission->health_at_entry = health;
        admission->reached_branch = exec_between(exec_events, exec_count, branch_pc,
                                                 exec_events[i].cycle, limit_cycle);
        admission->reached_health_store = exec_between(exec_events, exec_count, health_store_pc,
                                                       exec_events[i].cycle, limit_cycle);
        admission->wrote_health = access_between(access_events, access_count, health_address,
                                                 health - 1, exec_events[i].cycle, limit_cycle);
        admission->reset_timer = access_between(access_events, access_count, timer_address, 45,
                                                exec_events[i].cycle, limit_cycle);
        if (!admission->reached_branch)
            die("handler admission did not reach the timer branch");
        if (admission->timer_at_entry > 0) {
            if (admission->reached_health_store || admission->wrote_health || admission->reset_timer)
                die("positive-timer admission was not suppressed");
            suppressed_count++;
        } else if (admission->reached_health_store && admission->wrote_health && admission->reset_timer) {
            positive_count++;
            if (first_positive_frame == 0)
                first_positive_frame = admission->frame;
            else if (second_positive_frame == 0)
                second_positive_frame = admission->frame;
        }
    }

    for (size_t i = 0; i < access_count; i++) {
        if (access_events[i].address == timer_address && access_events[i].new_value == 0 &&
            access_events[i].frame > first_positive_frame) {
            first_expiry_frame = access_events[i].frame;
            break;
        }
    }
    if (admission_count < 4)
        die("too few native handler admissions");
    if (positive_count < 2 || first_positive_frame == 0 || second_positive_frame == 0)
        die("missing pre-window or post-expiry positive control");
    if (suppressed_count < 1)
        die("missing admitted contact during positive timer");
    if (first_expiry_frame == 0 || second_positive_frame <= first_expiry_frame)
        die("post-expiry positive control does not follow observed timer expiry");

    printf("{\n");
    printf("  \"schema\": \"abl-phase4-d03-runtime-v1\",\n");
    printf("  \"guard_passed\": true,\n");
    printf("  \"intervention\": \"none\",\n");
    printf("  \"handler_entries\": %zu,\n", admission_count);
    printf("  \"positive_entries\": %zu,\n", positive_count);
    printf("  \"suppressed_positive_timer_entries\": %zu,\n", suppressed_count);
    printf("  \"first_positive_frame\": %" PRIu64 ",\n", first_positive_frame);
    printf("  \"first_timer_expiry_frame\": %" PRIu64 ",\n", first_expiry_frame);
    printf("  \"post_expiry_positive_frame\": %" PRIu64 ",\n", second_positive_frame);
    printf("  \"admissions\": [\n");
    for (size_t i = 0; i < admission_count; i++) {
        const Admission *a = &admissions[i];
        printf("    {\"frame\":%" PRIu64 ",\"cycle\":%" PRIu64
               ",\"timer_at_entry\":%d,\"health_at_entry\":%d,"
               "\"health_store\":%s,\"health_write\":%s,\"timer_reset_45\":%s}%s\n",
               a->frame, a->cycle, a->timer_at_entry, a->health_at_entry,
               a->reached_health_store ? "true" : "false",
               a->wrote_health ? "true" : "false",
               a->reset_timer ? "true" : "false",
               i + 1 == admission_count ? "" : ",");
    }
    printf("  ]\n}\n");
    return 0;
}
