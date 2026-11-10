param(
    [string]$Direccion,
    [int]$Puerto = 0,
    [switch]$Recargar,
    [switch]$SinInstalar
)

$ErrorActionPreference = "Stop"
$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $raiz

$direccionExplicita = [bool]$Direccion -or [bool]$env:SERVICIO_HOST
$puertoExplicito = ($Puerto -gt 0) -or [bool]$env:SERVICIO_PORT

if (-not $Direccion) {
    if ($env:SERVICIO_HOST) { $Direccion = $env:SERVICIO_HOST } else { $Direccion = "127.0.0.1" }
}
if ($Puerto -le 0) {
    if ($env:SERVICIO_PORT) { $Puerto = [int]$env:SERVICIO_PORT } else { $Puerto = 8000 }
}

$pythonExe = $null
$pyArgs = @()
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    & py -3.12 -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $pythonExe = "py"
        $pyArgs = @("-3.12")
    }
}
if (-not $pythonExe) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "No se encontró Python. Instala Python 3.12 y vuelve a intentar."
    }
    $pythonExe = $python.Source
}

$venv = Join-Path $raiz ".venv"
$pythonVenv = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonVenv)) {
    Write-Host "Creando entorno virtual en .venv ..." -ForegroundColor Cyan
    if ($pyArgs.Count -gt 0) {
        & $pythonExe @pyArgs -m venv $venv
    } else {
        & $pythonExe -m venv $venv
    }
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual." }
}

$requirements = Join-Path $raiz "requirements.txt"
$marcador = Join-Path $venv ".dependencias-ok"
$instalar = $true
if ((Test-Path -LiteralPath $marcador) -and (Test-Path -LiteralPath $requirements)) {
    if ((Get-Item -LiteralPath $marcador).LastWriteTime -ge (Get-Item -LiteralPath $requirements).LastWriteTime) {
        $instalar = $false
    }
}
if ($instalar -and -not $SinInstalar) {
    Write-Host "Instalando dependencias ..." -ForegroundColor Cyan
    & $pythonVenv -m pip install --upgrade pip
    & $pythonVenv -m pip install -r $requirements
    if ($LASTEXITCODE -ne 0) { throw "Falló la instalación de dependencias." }
    New-Item -ItemType File -Force -Path $marcador | Out-Null
}

$envPath = Join-Path $raiz ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    $plantilla = Join-Path $raiz ".env.example"
    $texto = Get-Content -Raw -Encoding UTF8 -LiteralPath $plantilla
    $clave = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")).Substring(0, 40)
    $texto = $texto -replace "(?m)^API_KEYS=.*$", "API_KEYS=$clave"
    [System.IO.File]::WriteAllText($envPath, $texto, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "Se creó .env con una clave aleatoria." -ForegroundColor Yellow
    Write-Host "La clave quedó guardada en .env; ábrelo para copiarla en la consola web." -ForegroundColor Yellow
    Write-Host "No compartas ese archivo ni lo incluyas en capturas." -ForegroundColor Yellow
} else {
    Write-Host "Usando .env existente." -ForegroundColor DarkGray
}

$valoresEnv = @{}
Get-Content -LiteralPath $envPath -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
        $valoresEnv[$matches[1]] = $matches[2].Trim().Trim('"').Trim("'")
    }
}
if (-not $direccionExplicita -and $valoresEnv["SERVICIO_HOST"]) {
    $Direccion = $valoresEnv["SERVICIO_HOST"]
}
if (-not $puertoExplicito -and $valoresEnv["SERVICIO_PORT"]) {
    $Puerto = [int]$valoresEnv["SERVICIO_PORT"]
}

Write-Host ""
Write-Host "Servicio: http://${Direccion}:$Puerto" -ForegroundColor Green
Write-Host "Docs:     http://${Direccion}:$Puerto/docs" -ForegroundColor Green

$whatsappActivo = $false
if ($valoresEnv.ContainsKey("WHATSAPP_HABILITADO")) {
    $valorWhatsapp = $valoresEnv["WHATSAPP_HABILITADO"].ToLowerInvariant()
    $whatsappActivo = $valorWhatsapp -in @("1", "true", "si", "sí", "yes", "on")
}

if ($whatsappActivo -and -not $Recargar) {
    Write-Host "WhatsApp: http://${Direccion}:$Puerto/whatsapp (puente Node en loopback)" -ForegroundColor Green
    Write-Host "Detén con Ctrl+C." -ForegroundColor DarkGray
    Write-Host ""
    $env:SERVICIO_HOST = $Direccion
    $env:SERVICIO_PORT = "$Puerto"
    & $pythonVenv (Join-Path $raiz "scripts\servidor.py")
    exit $LASTEXITCODE
}

Write-Host "Detén con Ctrl+C." -ForegroundColor DarkGray
Write-Host ""

$argumentos = @(
    "-m", "uvicorn", "app.main:crear_app", "--factory",
    "--host", $Direccion, "--port", "$Puerto"
)
if ($Recargar) { $argumentos += "--reload" }

& $pythonVenv @argumentos
