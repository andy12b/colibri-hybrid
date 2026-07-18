import os
import sys
import numpy as np
from collections import defaultdict

def aggregate(tsv_file, output_file, usage_file="D:\\glm52_i4\\.coli_usage"):
    print(f"Reading {tsv_file}...")
    
    # Store counts of experts per token_id and layer
    # counts[token_id][layer][expert_id] = count
    counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    
    # Also keep a sequence of calls to replay for cache simulation
    # calls = [(token_id, layer, expert_id), ...]
    calls = []
    
    if not os.path.exists(tsv_file):
        print(f"Error: {tsv_file} not found.")
        return

    with open(tsv_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                token_id = int(parts[0])
                layer = int(parts[1])
                experts = [int(e) for e in parts[2].split(",") if e]
                
                for e in experts:
                    counts[token_id][layer][e] += 1
                    calls.append((token_id, layer, e))
    
    total_moe_calls = len(calls)
    print(f"Processed {total_moe_calls} expert allocations.")
    
    if total_moe_calls == 0:
        print("No data found. Exiting.")
        return

    # Build the top-8 table
    max_token = max(counts.keys()) if counts else 0
    max_layer = max(max(counts[tok].keys()) for tok in counts if counts[tok])
    
    vocab_size = max(155000, max_token + 1)
    num_layers = max_layer + 1
    
    # top-8 table
    table = np.full((vocab_size, num_layers, 8), -1, dtype=np.int16)
    
    for tok, layers in counts.items():
        for layer, exp_counts in layers.items():
            sorted_exp = sorted(exp_counts.items(), key=lambda x: x[1], reverse=True)
            top_8 = [e for e, count in sorted_exp[:8]]
            while len(top_8) < 8:
                top_8.append(-1)
            table[tok, layer] = top_8

    print(f"Built top-8 table.")

    # Read pinned experts
    pinned = set()
    if os.path.exists(usage_file):
        print(f"Loading pinned experts from {usage_file}")
        usage_counts = []
        with open(usage_file, "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) == 3:
                    layer, eid, cnt = map(int, parts)
                    usage_counts.append((layer, eid, cnt))
        usage_counts.sort(key=lambda x: x[2], reverse=True)
        # PIN=auto pins top 528
        for layer, eid, _ in usage_counts[:528]:
            pinned.add((layer, eid))
        print(f"Pinned {len(pinned)} experts.")
    else:
        print(f"Warning: {usage_file} not found. Assuming no pinned experts.")

    # Simulate LRU cache per layer (cap=1 unpinned expert per layer)
    cache = {l: [] for l in range(num_layers)}
    CAP = 1
    
    total_misses = 0
    covered_misses = 0
    
    for token_id, layer, eid in calls:
        if (layer, eid) in pinned:
            continue # Not a miss
            
        c = cache[layer]
        if eid in c:
            # Hit in unpinned cache
            c.remove(eid)
            c.append(eid)
        else:
            # MISS!
            total_misses += 1
            # Did our top-8 table predict this?
            if eid in table[token_id, layer]:
                covered_misses += 1
            
            # Update cache
            c.append(eid)
            if len(c) > CAP:
                c.pop(0)

    miss_coverage = (covered_misses / total_misses * 100) if total_misses > 0 else 0
    print(f"Total Misses: {total_misses}")
    print(f"Covered Misses: {covered_misses}")
    print(f"Miss Coverage by Top-8 Table: {miss_coverage:.2f}%")

    # Save as compact NPZ
    output_npz = "D:\\moe_top8_table.npz"
    np.savez_compressed(output_npz, table=table)
    print(f"Saved to {output_npz}")
    
    # Export flat binary for C-engine (Task 18 preparation)
    bin_file = "D:\\moe_top8_table.bin"
    table.tofile(bin_file)
    print(f"Exported flat binary to {bin_file}")

    # Append coverage to report
    with open("GEMINI_REPORT.md", "a", encoding="utf-8") as f:
        f.write(f"\n### TASK 19: Updated MoE Coverage Analysis\n")
        f.write(f"- Extended table to top-8 experts per (token, layer).\n")
        f.write(f"- Exported flat binary to `{bin_file}`.\n")
        f.write(f"- Simulated cache: PIN=auto (528) + CAP=1.\n")
        f.write(f"- Total MISS-es: {total_misses}\n")
        f.write(f"- Covered MISS-es by top-8 table: {covered_misses}\n")
        f.write(f"- **Real prefetch coverage (Miss Coverage): {miss_coverage:.2f}%**\n")

if __name__ == "__main__":
    aggregate("D:\\moe_instrument.tsv", "D:\\moe_top4_table.npz")
