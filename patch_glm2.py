import re
import sys

def patch(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add g_moe_log_file to top
    content = "#ifdef INSTRUMENT_MOE\nFILE *g_moe_log_file = NULL;\n#endif\n" + content
    
    # Patch main()
    content = content.replace("int main(int argc, char **argv){", 
                              "int main(int argc, char **argv){\n#ifdef INSTRUMENT_MOE\n    g_moe_log_file = fopen(\"D:\\\\moe_instrument.tsv\", \"a\");\n#endif\n")
    
    # Patch moe signature
    content = content.replace("static void moe(Model *m, Layer *l, int layer, float *x, int S, float *out, int with_shared){",
                              "#ifdef INSTRUMENT_MOE\nextern FILE *g_moe_log_file;\n#endif\nstatic void moe(Model *m, Layer *l, int layer, float *x, int S, float *out, int with_shared, const int *tokens){")

    # Patch route hits loop
    content = content.replace("for(int r=0;r<Ksel;r++) m->route_hits+=(expert_is_resident(m,layer,idx[r])?1:0);",
                              "for(int r=0;r<Ksel;r++) m->route_hits+=(expert_is_resident(m,layer,idx[r])?1:0);\n" +
                              "#ifdef INSTRUMENT_MOE\n" +
                              "            if (g_moe_log_file && tokens) {\n" +
                              "                fprintf(g_moe_log_file, \"%d\\t%d\\t\", tokens[s], layer);\n" +
                              "                for(int r=0; r<Ksel; r++) {\n" +
                              "                    fprintf(g_moe_log_file, \"%d%s\", idx[r], r==Ksel-1 ? \"\" : \",\");\n" +
                              "                }\n" +
                              "                fprintf(g_moe_log_file, \"\\n\");\n" +
                              "            }\n" +
                              "#endif\n")

    # Patch rank w loop
    content = content.replace("for(int kk=0;kk<Ksel;kk++) w[kk] = rank_w[kk]/tot;",
                              "for(int kk=0;kk<Ksel;kk++) w[kk] = rank_w[kk]/tot;\n" +
                              "#ifdef INSTRUMENT_MOE\n" +
                              "                if (g_moe_log_file && tokens) {\n" +
                              "                    fprintf(g_moe_log_file, \"%d\\t%d\\t\", tokens[s], layer);\n" +
                              "                    for(int r=0; r<Ksel; r++) {\n" +
                              "                        fprintf(g_moe_log_file, \"%d%s\", idx[r], r==Ksel-1 ? \"\" : \",\");\n" +
                              "                    }\n" +
                              "                    fprintf(g_moe_log_file, \"\\n\");\n" +
                              "                }\n" +
                              "#endif\n")

    # Patch moe calls
    content = content.replace("moe(m,l,li,nrm_host,S,out_host,0);", "moe(m,l,li,nrm_host,S,out_host,0,tokens);")
    content = content.replace("moe(m,l,li,lnrm,S,tmp,1);", "moe(m,l,li,lnrm,S,tmp,1,tokens);")
    content = content.replace("moe(m,l,li,nrm,S,tmp,1)", "moe(m,l,li,nrm,S,tmp,1,tokens)")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    patch(sys.argv[1])
