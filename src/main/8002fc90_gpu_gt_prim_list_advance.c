/* gpu_gt_prim_list_advance - walk prim list by tag stride (52->+36, 60->+48) until zero; return p+4. */
char *gpu_gt_prim_list_advance(char *p)
{
    unsigned int code = (unsigned char)p[3];
    if (code != 0) {
        do {
            switch (code & 0x7c) {
            case 52:
                p += 36;
                break;
            case 60:
                p += 48;
                break;
            }
            code = (unsigned char)p[3];
        } while (code != 0);
    }
    return p + 4;
}
