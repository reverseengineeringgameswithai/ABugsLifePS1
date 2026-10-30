/* advances a parse cursor past a variable-length record into the gp cursor global. Layout UNKNOWN. */
extern char *g_80082234;

void advance_parse_cursor_past_record(char *p)
{
    unsigned short n = *(unsigned short *)(p + 8);
    g_80082234 = p + (n * 2 + 12);
}
