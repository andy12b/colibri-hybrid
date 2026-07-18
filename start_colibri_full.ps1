# Launcher complet Colibri: motor + middleware + interfata web + Edge
# Nu porneste dublu: sare peste componentele care ruleaza deja.
$ErrorActionPreference = 'SilentlyContinue'

function PortUp($p) {
    [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
}

# 1. Motorul (8080) — pornirea creste pagefile-ul, deci doar daca e jos
if (-not (PortUp 8080)) {
    Start-Process 'D:\project colibri\start_engine_eco.cmd' -WindowStyle Hidden
}

# 2. Middleware (8000)
if (-not (PortUp 8000)) {
    Start-Process 'D:\project colibri\start_middleware.cmd' -WindowStyle Hidden
}

# 3. Interfata web Vite (5173)
if (-not (PortUp 5173)) {
    Start-Process cmd -ArgumentList '/c', 'npm run dev --prefix web > "D:\project colibri\vite.log" 2>&1' `
        -WorkingDirectory 'D:\project_colibri_engine' -WindowStyle Hidden
}

# 4. Astept interfata si middleware-ul (max 90s), apoi deschid Edge
for ($i = 0; $i -lt 45; $i++) {
    if ((PortUp 5173) -and (PortUp 8000)) { break }
    Start-Sleep -Seconds 2
}
Start-Process msedge 'http://localhost:5173'
# Motorul mare se incarca in fundal 1-2 minute; interfata ii arata statusul.

