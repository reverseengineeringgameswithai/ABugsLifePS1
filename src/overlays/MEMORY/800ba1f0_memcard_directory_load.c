extern int sub_800ba030(void);
extern int sub_800bd6c8(int port);

int memcard_directory_load_for_slot(int slot)
{
    sub_800ba030();
    if (slot)
        return sub_800bd6c8(0x10);
    return sub_800bd6c8(0);
}
