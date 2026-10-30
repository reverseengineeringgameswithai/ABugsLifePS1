meta:
  id: abl_level_raw_container
  title: ABL LEVEL.RAW chunk container
  endian: be
  license: CC0-1.0
doc: >
  Read-only framing schema. Chunk payload semantics are defined separately and
  retail-derived instances stay external.
seq:
  - id: chunks
    type: chunk
    repeat: until
    repeat-until: _.decompressed_size == 0xffffffff
types:
  chunk:
    seq:
      - {id: decompressed_size, type: u4}
      - id: compressed_size
        type: u4
        if: decompressed_size != 0xffffffff
      - id: preserved_header
        size: 6
        if: decompressed_size != 0xffffffff
      - id: compressed_stream
        size: compressed_size
        if: decompressed_size != 0xffffffff
