/* load_named_file @ 0x8002ffa8 — build "<name><suffix>" in a stack path buffer,
 * load it through the universal loader (with *info as the mode), then hand the
 * remaining two args to the post-load handler. */
extern char *strcpy(char *, const char *);
extern char *strcat(char *, const char *);
extern char g_80082128[];     /* filename suffix */
extern int universal_file_loader(char *, int);
extern void sub_8002fce8(int, int *);

void load_named_file(char *name, int arg, int *info)
{
    char path[128];
    strcpy(path, name);
    strcat(path, g_80082128);
    universal_file_loader(path, *info);
    sub_8002fce8(arg, info);
}
