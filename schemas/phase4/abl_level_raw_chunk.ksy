meta:
  id: abl_level_raw_chunk
  title: ABL LEVEL.RAW compressed chunk envelope
  endian: be
  license: CC0-1.0
doc: >
  Read-only envelope schema for bounded decompressor inputs. It intentionally
  does not describe the instruction-level bitstream grammar.
seq:
  - {id: decompressed_size, type: u4}
  - {id: compressed_size, type: u4}
  - {id: preserved_header, size: 6}
  - {id: compressed_stream, size: compressed_size}
