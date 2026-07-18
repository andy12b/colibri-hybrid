import os
import json
import struct

def parse_safetensors_metadata(filepath):
    with open(filepath, 'rb') as f:
        length_bytes = f.read(8)
        if not length_bytes:
            return None
        length = struct.unpack('<Q', length_bytes)[0]
        header_bytes = f.read(length)
        header = json.loads(header_bytes.decode('utf-8'))
        return header

filepath = r"D:\glm52_i4\out-mtp-00000.safetensors"
header = parse_safetensors_metadata(filepath)
if header:
    for k, v in header.items():
        if k != '__metadata__':
            print(f"{k}: {v['dtype']} {v['shape']}")
