meta:
  id: abl_seed_table
  title: ABL decompressed seed placement table
  endian: le
  license: CC0-1.0
doc: >
  Read-only schema for a synthetic or externally provisioned decompressed seed
  table. Retail-derived instances stay external.
seq:
  - id: marker
    type: u4
    valid: 0x23
  - id: records
    type: seed_record
    repeat: eos
types:
  seed_record:
    seq:
      - {id: x, type: s4}
      - {id: y, type: s4}
      - {id: z, type: s4}
      - {id: metadata, size: 16}
