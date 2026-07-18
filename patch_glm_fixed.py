import sys

def patch(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add g_moe_log_file to the top after includes
    content = content.replace("#include <stdlib.h>", 
                              "#include <stdlib.h>\n#ifdef INSTRUMENT_MOE\nFILE *g_moe_log_file = NULL;\nconst int *g_moe_log_tokens = NULL;\n#endif\n")
    
    # Patch main()
    content = content.replace("int main(int argc, char **argv){", 
                              "int main(int argc, char **argv){\n#ifdef INSTRUMENT_MOE\n    g_moe_log_file = fopen(\"D:\\\\moe_instrument.tsv\", \"a\");\n#endif\n")
    
    # Patch moe() to use g_moe_log_tokens
    content = content.replace("m->route_slots+=(uint64_t)Ksel;",
                              "m->route_slots+=(uint64_t)Ksel;\n" +
                              "#ifdef INSTRUMENT_MOE\n" +
                              "            if (g_moe_log_file && g_moe_log_tokens) {\n" +
                              "                fprintf(g_moe_log_file, \"%d\\t%d\\t\", g_moe_log_tokens[s], layer);\n" +
                              "                for(int r=0; r<Ksel; r++) {\n" +
                              "                    fprintf(g_moe_log_file, \"%d%s\", idx[r], r==Ksel-1 ? \"\" : \",\");\n" +
                              "                }\n" +
                              "                fprintf(g_moe_log_file, \"\\n\");\n" +
                              "                fflush(g_moe_log_file);\n" +
                              "            }\n" +
                              "#endif\n")

    # Patch step() and step_all() to set g_moe_log_tokens
    content = content.replace("layers_forward(m,x,S,pos_base);",
                              "#ifdef INSTRUMENT_MOE\n    g_moe_log_tokens = ids;\n#endif\n    layers_forward(m,x,S,pos_base);")
    content = content.replace("layers_forward(m,x,S,0);",
                              "#ifdef INSTRUMENT_MOE\n    g_moe_log_tokens = ids;\n#endif\n    layers_forward(m,x,S,0);")
    content = content.replace("layers_forward(m,x,T,0);",
                              "#ifdef INSTRUMENT_MOE\n    g_moe_log_tokens = ids;\n#endif\n    layers_forward(m,x,T,0);")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    patch(sys.argv[1])
