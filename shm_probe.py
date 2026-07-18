import ctypes

k32 = ctypes.windll.kernel32
k32.OpenFileMappingA.restype = ctypes.c_void_p
k32.MapViewOfFile.restype = ctypes.c_void_p
FILE_MAP_READ = 4
h = k32.OpenFileMappingA(FILE_MAP_READ, False, b"Local\\ColibriDraftShm")
if not h:
    print("SHM not found (draft server down?)")
    raise SystemExit(1)
SHM_SIZE = 4 + 4 + 4096 * 4 + 4 + 128 * 4
p = k32.MapViewOfFile(h, FILE_MAP_READ, 0, 0, SHM_SIZE)
buf = (ctypes.c_int32 * (SHM_SIZE // 4)).from_address(p)
state, ctx_len = buf[0], buf[1]
draft_len = buf[2 + 4096]
drafts = [buf[2 + 4096 + 1 + i] for i in range(max(0, min(draft_len, 8)))]
ctx_tail = [buf[2 + max(0, ctx_len - 6) + i] for i in range(max(0, min(6, ctx_len)))]
print(f"state={state} context_length={ctx_len} draft_length={draft_len}")
print(f"last ctx tokens: {ctx_tail}")
print(f"draft tokens: {drafts}")
