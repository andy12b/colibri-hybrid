import subprocess
import os

prompts = [
    "P1: Cum funcționează un motor MoE?",
    "P2: Write a Python script to compute the Fibonacci sequence.",
    "P3: Explain speculative decoding in large language models.",
    "Ce este fotosinteza?",
    "Write a C program to reverse a string.",
    "Define 'entropy' in the context of information theory.",
    "Cum se prepară mămăliga?",
    "Can you write a regex for an email address?",
    "Explique-moi la relativité restreinte.",
    "Write a SQL query to find the second highest salary."
]

env = os.environ.copy()
env["COLI_ENGINE"] = r"D:\project_colibri_engine\c\glm_test.exe"
env["COLI_RAM_OVERCOMMIT"] = "1"

with open("task15_outputs.txt", "w", encoding="utf-8") as f:
    for i, p in enumerate(prompts):
        print(f"Running prompt {i+1}/{len(prompts)}...")
        f.write(f"--- Prompt {i+1} ---\n{p}\n")
        
        proc = subprocess.run(
            [r"D:\project colibri\.venv\Scripts\python.exe", r"D:\project_colibri_engine\c\coli", "run", "--model", r"D:\glm52_i4", "--ram", "12", p],
            env=env,
            capture_output=True,
            text=True
        )
        
        f.write(f"STDOUT:\n{proc.stdout}\n")
        f.write(f"STDERR:\n{proc.stderr}\n\n")

print("Done running task 15 prompts.")
