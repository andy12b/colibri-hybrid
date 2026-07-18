import sys

def patch_glm(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    out_lines = []
    for i, line in enumerate(lines):
        if line.startswith("static void moe(Model *m, Layer *l, int layer, float *x, int S, float *out, int with_shared){"):
            out_lines.append("#ifdef INSTRUMENT_MOE\nextern FILE *g_moe_log_file;\n#endif\n")
            out_lines.append("static void moe(Model *m, Layer *l, int layer, float *x, int S, float *out, int with_shared, const int *tokens){\n")
        elif "for(int r=0;r<Ksel;r++) m->route_hits+=(expert_is_resident(m,layer,idx[r])?1:0);" in line:
            out_lines.append(line)
            out_lines.append("""#ifdef INSTRUMENT_MOE
            if (g_moe_log_file && tokens) {
                fprintf(g_moe_log_file, "%d\\t%d\\t", tokens[s], layer);
                for(int r=0; r<Ksel; r++) {
                    fprintf(g_moe_log_file, "%d%s", idx[r], r==Ksel-1 ? "" : ",");
                }
                fprintf(g_moe_log_file, "\\n");
            }
#endif
""")
        elif "for(int kk=0;kk<Ksel;kk++) w[kk] = rank_w[kk]/tot;" in line:
            out_lines.append(line)
            out_lines.append("""#ifdef INSTRUMENT_MOE
                if (g_moe_log_file && tokens) {
                    fprintf(g_moe_log_file, "%d\\t%d\\t", tokens[s], layer);
                    for(int r=0; r<Ksel; r++) {
                        fprintf(g_moe_log_file, "%d%s", idx[r], r==Ksel-1 ? "" : ",");
                    }
                    fprintf(g_moe_log_file, "\\n");
                }
#endif
""")
        elif "moe(m,l,li,nrm_host,S,out_host,0);" in line:
            out_lines.append(line.replace("moe(m,l,li,nrm_host,S,out_host,0);", "moe(m,l,li,nrm_host,S,out_host,0,tokens);"))
        elif "moe(m,l,li,lnrm,S,tmp,1);" in line:
            out_lines.append(line.replace("moe(m,l,li,lnrm,S,tmp,1);", "moe(m,l,li,lnrm,S,tmp,1,tokens);"))
        elif "if(l->sparse) moe(m,l,li,nrm,S,tmp,1); else dense_mlp(l,nrm,S,D,c->dense_inter,tmp);" in line:
            out_lines.append(line.replace("moe(m,l,li,nrm,S,tmp,1)", "moe(m,l,li,nrm,S,tmp,1,tokens)"))
        elif "int main(int argc, char **argv){" in line:
            out_lines.append(line)
            out_lines.append("""#ifdef INSTRUMENT_MOE
    g_moe_log_file = fopen("D:\\\\moe_instrument.tsv", "a");
#endif
""")
        elif "FILE *g_moe_log_file = NULL;" not in out_lines and "int main(" in line:
            out_lines.insert(0, "#ifdef INSTRUMENT_MOE\\nFILE *g_moe_log_file = NULL;\\n#endif\\n")
            out_lines.append(line)
        else:
            out_lines.append(line)
            
    # Make sure global var is declared
    if not any("FILE *g_moe_log_file" in l for l in out_lines):
        out_lines.insert(0, "#ifdef INSTRUMENT_MOE\\nFILE *g_moe_log_file = NULL;\\n#endif\\n")
            
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)
        
if __name__ == "__main__":
    patch_glm(sys.argv[1])
