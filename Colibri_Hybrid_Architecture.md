# Arhitectură Hibridă de Accelerare pentru Colibrì (GLM-5.2) - Propunere

Aceasta este o schiță a arhitecturii discutate, pregătită pentru implementare după ce ai rezolvat cu spațiul de stocare. Sistemul este gândit să folosească GPU-ul în repaus (RTX 5060, 8GB VRAM) pentru a acționa ca un "asistent de drafting și traducere" pentru gigantul GLM-5.2 care rulează de pe SSD.

## 1. Speculative Decoding (Draft & Verify)

### Abordare propusă: Integrare externă prin server API compatibil OpenAI
Pentru a nu supraîncărca sursa principală Colibrì cu modificări masive (până nu dovedim conceptul), vom scrie un script Python intermediar (proxy/middleware).

**Fluxul:**
1. **Drafting pe GPU (Python):** Rulăm un model mic de 1.5B (ex. Qwen1.5-1.8B sau Llama-3-8B puternic cuantizat pentru a încăpea în cei 8GB VRAM). Acesta generează un calup de tokeni-propunere (draft).
2. **Conexiunea cu Colibrì:** Scriptul nostru trimite acest calup prin API-ul local OpenAI deja expus de Colibrì (sau conectat la interfața `spec_decode` internă prin extensie C/Python).
3. **Verification (Colibrì / SSD):** GLM-5.2 face un single-pass peste calup. Acceptă secvența corectă. Dacă pică un token, se oprește și regenerează el de acolo.

*Avantaj:* Qwen/Llama este extrem de rapid în VRAM și are o rată de acceptare (hit rate) vizibil mai bună decât N-grams.

## 2. Arhitectura în Cascadă și Comprimarea I/O

**Etapa A: Comprimare (GLM-5.2 pe SSD)**
Vom injecta în cererile către Colibrì un System Prompt strict:
```text
"Răspunde întotdeauna EXCLUSIV în limba chineză. Fii ultra-concis, folosește doar concepte esențiale. Nu folosi cuvinte de umplutură. Dacă trebuie să scrii cod, scrie codul direct, fără explicații adiționale."
```
GLM-5.2 va scoate un șir foarte dens de caractere chinezești. Timpul petrecut pentru generare se reduce masiv deoarece numărul de tokeni scade dramatic.

**Etapa B: Extindere & Traducere (GPU)**
1. Scriptul nostru Python captează acest output chinezesc.
2. În GPU avem încărcat un model de traducere/reformulare foarte rapid.
3. El preia outputul: `GLM_Output_Chineză -> Extindere & Traducere Engleză/Română`.

### Regula de Aur (Codul Agentic)
Pentru a evita "stricarea" codului generat:
Vom folosi un analizor Regex integrat în Python (middleware-ul nostru) care să extragă blocurile de cod ``` înainte de a trimite textul la tradus pe GPU.
Exemplu de logică Python:
```python
import re

def process_glm_output(raw_output):
    # Extrage codul brut
    code_blocks = re.findall(r'```.*?```', raw_output, re.DOTALL)
    text_only = re.sub(r'```.*?```', '[CODE_BLOCK_PLACEHOLDER]', raw_output, flags=re.DOTALL)
    
    # Trimitem `text_only` la traducătorul GPU
    translated_text = translate_on_gpu(text_only)
    
    # Reasamblăm
    for code in code_blocks:
        translated_text = translated_text.replace('[CODE_BLOCK_PLACEHOLDER]', code, 1)
        
    return translated_text
```

Această arhitectură separă clar logica (GLM/SSD) de redactare/viteză (GPU/VRAM) și adresează direct bottleneck-ul SSD-ului. Vom putea începe prototiparea acestui middleware imediat ce ești gata.
