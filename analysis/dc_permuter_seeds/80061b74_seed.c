extern void AddPrim(unsigned int *ot, unsigned int *p);
void AddPrim(unsigned int *ot, unsigned int *p)
{
    *p = (*p & 0xff000000) | (*ot & 0x00ffffff);
    *ot = (*ot & 0xff000000) | ((unsigned int)p & 0x00ffffff);
}
