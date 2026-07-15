import torch

def verify_system():
    print("--- System Verification for Colibri ---")
    if torch.cuda.is_available():
        device = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[OK] CUDA available! Device: {device}")
        print(f"[OK] Total VRAM: {vram_gb:.2f} GB")
        
        if vram_gb < 8.0:
            print("[WARNING] Less than 8GB VRAM detected. Llama-3-8B might struggle. Consider Qwen-1.5-1.8B.")
        else:
            print("[OK] VRAM is sufficient for quantization (8GB+).")
            
        # Protect memory: limit to 90% of VRAM to prevent system crashes
        torch.cuda.set_per_process_memory_fraction(0.9, 0)
        print("[OK] VRAM usage limited to 90% to prevent GPU throttling and overheating.")
    else:
        print("[ERROR] CUDA is not available! The system will fall back to CPU, which defeats the hybrid architecture.")

if __name__ == '__main__':
    verify_system()
