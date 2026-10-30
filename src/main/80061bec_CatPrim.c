/* CatPrim @ 0x80061bec - set prim p's next-address field (low 24 bits) to next. */
void CatPrim(unsigned int *p, unsigned int next)
{
    *p = (*p & 0xff000000) | (next & 0x00ffffff);
}
