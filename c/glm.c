#ifdef INSTRUMENT_MOE
FILE *g_moe_log_file = NULL;
#endif
#ifdef INSTRUMENT_MOE\nFILE *g_moe_log_file = NULL;\n#endif\n#include <windows.h>
#include <stdio.h>
#include <stdint.h>

#define SHM_NAME "Local\\ColibriDraftShm"
#define SHM_SIZE (4 + 4 + 4096*4 + 4 + 128*4)
#define IPC_TIMEOUT_MS 3000 // Max wait time for GPU draft (milliseconds)

typedef struct {
    int32_t state; // Deprecated by Events, keeping for struct alignment
    int32_t context_length;
    int32_t context_tokens[4096];
    int32_t draft_length;
    int32_t draft_tokens[128];
} SharedDraftMemory;

static SharedDraftMemory* d_shm = NULL;
static HANDLE hMapFile = NULL;
static HANDLE hEvent_C_Ready = NULL;
static HANDLE hEvent_GPU_Ready = NULL;

// Call this during Colibri initialization
void init_ipc_drafting() {
    hMapFile = OpenFileMappingA(FILE_MAP_ALL_ACCESS, FALSE, SHM_NAME);
    if (hMapFile == NULL) {
        printf("[WARN] Could not open shared memory object (%lu). GPU Drafting disabled.\n", GetLastError());
        return;
    }
    d_shm = (SharedDraftMemory*) MapViewOfFile(hMapFile, FILE_MAP_ALL_ACCESS, 0, 0, SHM_SIZE);
    
    // Initialize Named Events for synchronization (Auto-Reset events)
    hEvent_C_Ready = CreateEventA(NULL, FALSE, FALSE, "Local\\Colibri_C_Ready");
    hEvent_GPU_Ready = CreateEventA(NULL, FALSE, FALSE, "Local\\Colibri_GPU_Ready");
    
    if (d_shm == NULL || hEvent_C_Ready == NULL || hEvent_GPU_Ready == NULL) {
        printf("[WARN] IPC Initialization failed (%lu).\n", GetLastError());
        if (d_shm) UnmapViewOfFile(d_shm);
        if (hMapFile) CloseHandle(hMapFile);
        d_shm = NULL;
    } else {
        printf("[INFO] Successfully connected to GPU Draft Shared Memory and Sync Events!\n");
    }
}

// Integrates into the spec_decode function
int get_ipc_draft_tokens(int* context, int context_len, int* draft_out, int max_drafts) {
    if (!d_shm) return 0; // Fallback to normal inference
    
    // Copy context to SHM
    d_shm->context_length = context_len > 4096 ? 4096 : context_len;
    for(int i = 0; i < d_shm->context_length; i++) {
        d_shm->context_tokens[i] = context[i];
    }
    
    // Memory barrier before signaling
    MemoryBarrier(); 
    
    // Clear any previous stale event flag just in case we are out of sync
    ResetEvent(hEvent_GPU_Ready);
    
    // Signal GPU that context is ready
    SetEvent(hEvent_C_Ready);
    
    // Wait for GPU to finish drafting (Timeout avoids indefinite block)
    DWORD wait_res = WaitForSingleObject(hEvent_GPU_Ready, IPC_TIMEOUT_MS);
    
    if (wait_res == WAIT_OBJECT_0) {
        // Retrieve drafts safely
        int count = d_shm->draft_length > max_drafts ? max_drafts : d_shm->draft_length;
        for(int i = 0; i < count; i++) {
            draft_out[i] = d_shm->draft_tokens[i];
        }
        return count;
    }
    
    // WAIT_TIMEOUT or other failure: fallback immediately to standard generation
    return 0;
}

void cleanup_ipc_drafting() {
    if (d_shm) UnmapViewOfFile(d_shm);
    if (hMapFile) CloseHandle(hMapFile);
    if (hEvent_C_Ready) CloseHandle(hEvent_C_Ready);
    if (hEvent_GPU_Ready) CloseHandle(hEvent_GPU_Ready);
}
