/* writes global 0x80080eb8 only if it differs from the arg. Global meaning UNKNOWN. */
extern int g_80080eb8;

void sound_state_set_if_changed(int value)
{
    int *p = &g_80080eb8;
    if (value != *p)
        *p = value;
}
