/* string_to_upper - in-place ASCII uppercase (lowercase byte + 224). */
void string_to_upper(char *s)
{
    if (*s == 0)
        return;
    do {
        if ((unsigned char)(*s - 'a') < 26U)
            *s = *s + 224;
        s++;
    } while (*s != 0);
}
