import numpy as np
import collections
import sys
import os
from tqdm import tqdm

def aggregate_tsv(tsv_path, out_npz="moe_speq_table.npz", vocab_size=151552, n_layers=40, top_k=4):
    print(f"Reading TSV: {tsv_path}")
    
    # We need to count frequencies of experts for each (token_id, layer).
    # Since tokens can be up to vocab_size and layers up to n_layers,
    # allocating a full array of dicts or counters is slow but feasible.
    # We can use a nested list of dictionaries: [token_id][layer] -> Counter(expert_id)
    
    # To save memory and time, we can parse line by line.
    counts = [[collections.Counter() for _ in range(n_layers)] for _ in range(vocab_size)]
    
    lines_read = 0
    with open(tsv_path, "r") as f:
        for line in tqdm(f, desc="Parsing TSV"):
            parts = line.strip().split("\t")
            if len(parts) < 3: continue
            
            token_id = int(parts[0])
            layer = int(parts[1])
            
            # parts[2:] are the experts
            experts = [int(e) for e in parts[2:]]
            
            if token_id < vocab_size and layer < n_layers:
                counts[token_id][layer].update(experts)
            
            lines_read += 1
            
    print(f"Read {lines_read} lines.")
    
    # Build the final table: shape [vocab_size, n_layers, top_k]
    # dtype int16 since experts are < 256. -1 means no data.
    table = np.full((vocab_size, n_layers, top_k), -1, dtype=np.int16)
    
    tokens_with_data = 0
    for t in tqdm(range(vocab_size), desc="Aggregating top-K"):
        has_data = False
        for l in range(n_layers):
            c = counts[t][l]
            if not c:
                continue
            has_data = True
            # Get top_k most common
            common = c.most_common(top_k)
            for i, (exp_id, freq) in enumerate(common):
                table[t, l, i] = exp_id
        if has_data:
            tokens_with_data += 1
            
    print(f"Tokens with coverage: {tokens_with_data} / {vocab_size} ({(tokens_with_data/vocab_size)*100:.2f}%)")
    
    np.savez_compressed(out_npz, table=table)
    print(f"Saved table to {out_npz}")

if __name__ == "__main__":
    tsv = sys.argv[1] if len(sys.argv) > 1 else "moe_log.tsv"
    out = sys.argv[2] if len(sys.argv) > 2 else "moe_speq_table.npz"
    aggregate_tsv(tsv, out)
