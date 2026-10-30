extern void sub_800bd720(void);
extern int sub_800bd710(int port, int sector, void *source);

int memcard_ack_card_change(int port)
{
    sub_800bd720();
    return sub_800bd710(port, 0x3f, 0);
}
