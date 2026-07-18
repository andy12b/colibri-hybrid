#include <stdio.h>
#include <windows.h>
#include <cpuid.h>

int main() {
    char cpu[256] = "Unknown";
#if defined(__x86_64__) || defined(__i386__)
    unsigned int r[12] = {0};
    unsigned int *w = r;
    for (unsigned int f = 0x80000002u; f <= 0x80000004u; f++, w += 4) {
        __get_cpuid(f, &w[0], &w[1], &w[2], &w[3]);
    }
    char *b = (char *)r;
    b[47] = 0;
    while (*b == ' ') b++;
    snprintf(cpu, sizeof(cpu), "%s", b);
    
    // Check AVX2
    unsigned int eax, ebx, ecx, edx;
    int has_avx2 = 0;
    if (__get_cpuid_max(0, NULL) >= 7) {
        __cpuid_count(7, 0, eax, ebx, ecx, edx);
        if (ebx & (1 << 5)) has_avx2 = 1;
    }
    
    printf("CPU Brand: %s\n", cpu);
    printf("AVX2 Supported: %s\n", has_avx2 ? "YES" : "NO");
#else
    printf("Not x86/x64\n");
#endif
    return 0;
}
