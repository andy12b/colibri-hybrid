import sys

with open(r"D:\project_colibri_engine\c\glm.c", "r", encoding="utf-8") as f:
    code = f.read()

counters = """
// --- SPEQ COUNTERS ---
static unsigned long long g_speq_enqueued = 0;
static unsigned long long g_speq_already_cached = 0;
static unsigned long long g_speq_hit = 0;
static unsigned long long g_speq_evicted_unused = 0;
"""
code = code.replace("static int g_mtp_off=0;", "static int g_mtp_off=0;\n" + counters)

struct_old = "int64_t slab_cap, fslab_cap; uint64_t used; } ESlot;"
struct_new = "int64_t slab_cap, fslab_cap; unsigned long long used; int speq_flag; int speq_hit; } ESlot;"
code = code.replace(struct_old, struct_new)

enqueue_old = """                    pilot_q[w & 4095].l = l; 
                    pilot_q[w & 4095].e = eid;
                    __atomic_store_n(&pilot_w, w + 1, __ATOMIC_RELEASE);"""
enqueue_new = enqueue_old + "\n                    __atomic_add_fetch(&g_speq_enqueued, 1, __ATOMIC_RELAXED);"
code = code.replace(enqueue_old, enqueue_new)

cache_pin = "for(int z=0;z<m->npin[layer];z++) if(P[z].eid==eid){ pthread_mutex_unlock(&g_pilot_mx); return; }"
cache_pin_new = "for(int z=0;z<m->npin[layer];z++) if(P[z].eid==eid){ __atomic_add_fetch(&g_speq_already_cached,1,__ATOMIC_RELAXED); pthread_mutex_unlock(&g_pilot_mx); return; }"
code = code.replace(cache_pin, cache_pin_new)

cache_ecn = "for(int z=0;z<nn;z++) if(Sl[z].eid==eid){ pthread_mutex_unlock(&g_pilot_mx); return; }"
cache_ecn_new = "for(int z=0;z<nn;z++) if(Sl[z].eid==eid){ __atomic_add_fetch(&g_speq_already_cached,1,__ATOMIC_RELAXED); pthread_mutex_unlock(&g_pilot_mx); return; }"
code = code.replace(cache_ecn, cache_ecn_new)

pilot_evict_old = "ESlot *dst=&Sl[slot];"
pilot_evict_new = "ESlot *dst=&Sl[slot];\n    if (!isnew && dst->speq_flag && !dst->speq_hit && dst->eid != -1) __atomic_add_fetch(&g_speq_evicted_unused, 1, __ATOMIC_RELAXED);\n    dst->speq_flag = 0; dst->speq_hit = 0;"
code = code.replace(pilot_evict_old, pilot_evict_new)

pilot_loaded_old = "if(isnew) m->ecn[layer]=slot+1;"
pilot_loaded_new = "dst->speq_flag = 1; dst->speq_hit = 0;\n        if(isnew) m->ecn[layer]=slot+1;"
code = code.replace(pilot_loaded_old, pilot_loaded_new)

moe_evict_old = "else { int lru=0; for(int z=1;z<m->ecap;z++) if(Sl[z].used<Sl[lru].used) lru=z; dst=&Sl[lru]; }"
moe_evict_new = moe_evict_old + "\n              if (dst->speq_flag && !dst->speq_hit && dst->eid != -1) __atomic_add_fetch(&g_speq_evicted_unused, 1, __ATOMIC_RELAXED);\n              dst->speq_flag = 0; dst->speq_hit = 0;"
code = code.replace(moe_evict_old, moe_evict_new)

hit_old = "for(int z=0;z<nn;z++) if(Sl[z].eid==eid){ m->hits++; Sl[z].used=(uint64_t)__atomic_add_fetch(&m->eclock,1,__ATOMIC_RELAXED); use[j]=&Sl[z]; break; }"
hit_new = "for(int z=0;z<nn;z++) if(Sl[z].eid==eid){ m->hits++; Sl[z].used=(unsigned long long)__atomic_add_fetch(&m->eclock,1,__ATOMIC_RELAXED); if(Sl[z].speq_flag && !Sl[z].speq_hit) { Sl[z].speq_hit=1; __atomic_add_fetch(&g_speq_hit,1,__ATOMIC_RELAXED); } use[j]=&Sl[z]; break; }"
code = code.replace(hit_old, hit_new)

print_old = "emitted++; m->n_emit++;"
print_new = "emitted++; m->n_emit++;\n        if (m->n_emit % 32 == 0) {\n            fprintf(stderr, \"[SPEQ] enq:%llu cached:%llu hit:%llu evicted:%llu\\n\", g_speq_enqueued, g_speq_already_cached, g_speq_hit, g_speq_evicted_unused);\n        }"
code = code.replace(print_old, print_new)

with open(r"D:\project_colibri_engine\c\glm_test_speq2.c", "w", encoding="utf-8") as f:
    f.write(code)

print("Patched glm_test_speq2.c successfully")
