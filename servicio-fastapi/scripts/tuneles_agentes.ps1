param(
    [int[]]$Puertos = @(2025, 2026, 2027, 2028),
    [int]$EsperaSegundos = 90,
    [switch]$Detener
)

# Abre un túnel temporal de Cloudflare por cada agente LangGraph local y escribe
# el valor listo para la Config Var A2A_SERVIDORES de Heroku.
#
# Uso:
#   .\scripts\tuneles_agentes.ps1                 # puertos 2025-2028
#   .\scripts\tuneles_agentes.ps1 -Puertos 2025   # solo un agente
#   .\scripts\tuneles_agentes.ps1 -Detener        # cierra todos
#
# Requiere cloudflared en el PATH y cada agente levantado:
#   langgraph dev --port 2025

$ErrorActionPreference = "Stop"
$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$carpetaLogs = Join-Path $raiz "logs"
New-Item -ItemType Directory -Force -Path $carpetaLogs | Out-Null
$archivoPids = Join-Path $carpetaLogs "tuneles.pids"
$archivoJson = Join-Path $carpetaLogs "tuneles.json"

if ($Detener) {
    if (Test-Path -LiteralPath $archivoPids) {
        foreach ($linea in Get-Content -LiteralPath $archivoPids) {
            if (-not $linea.Trim()) { continue }
            try {
                Stop-Process -Id ([int]$linea) -Force -ErrorAction Stop
                Write-Host "Túnel detenido (PID $linea)."
            } catch {
                Write-Host "El proceso $linea ya no estaba corriendo."
            }
        }
        Remove-Item -LiteralPath $archivoPids -Force
    } else {
        Write-Host "No hay túneles registrados."
    }
    Remove-Item -LiteralPath $archivoJson -Force -ErrorAction SilentlyContinue
    Get-ChildItem -LiteralPath $carpetaLogs -Filter "tunel-*.log" -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
    return
}

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    throw "No se encontró cloudflared. Instálalo con: winget install Cloudflare.cloudflared"
}

$patron = [regex]"https://[a-z0-9-]+\.trycloudflare\.com"
$pids = @()
$urls = [ordered]@{}

foreach ($puerto in $Puertos) {
    $activo = $false
    try {
        $activo = (Invoke-WebRequest -Uri "http://127.0.0.1:$puerto/ok" -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200
    } catch {
        $activo = $false
    }
    if (-not $activo) {
        Write-Warning "El puerto $puerto no responde en /ok; se omite. Levántalo con: langgraph dev --port $puerto"
        continue
    }

    $logOut = Join-Path $carpetaLogs "tunel-$puerto.log"
    $logErr = Join-Path $carpetaLogs "tunel-$puerto.err.log"
    Remove-Item -LiteralPath $logOut, $logErr -Force -ErrorAction SilentlyContinue

    Write-Host "Abriendo túnel para el puerto $puerto ..." -ForegroundColor Cyan
    $proceso = Start-Process -FilePath $cloudflared.Source `
        -ArgumentList @("tunnel", "--url", "http://127.0.0.1:$puerto", "--no-autoupdate") `
        -RedirectStandardOutput $logOut -RedirectStandardError $logErr `
        -WindowStyle Hidden -PassThru
    $pids += $proceso.Id

    $limite = (Get-Date).AddSeconds($EsperaSegundos)
    $url = $null
    while ((Get-Date) -lt $limite -and -not $url) {
        foreach ($archivo in @($logOut, $logErr)) {
            if (-not (Test-Path -LiteralPath $archivo)) { continue }
            $texto = Get-Content -LiteralPath $archivo -Raw -ErrorAction SilentlyContinue
            if (-not $texto) { continue }
            $coincidencia = $patron.Match($texto)
            if ($coincidencia.Success) { $url = $coincidencia.Value; break }
        }
        if ($proceso.HasExited) { break }
        if (-not $url) { Start-Sleep -Milliseconds 500 }
    }

    if (-not $url) {
        Write-Warning "No se pudo leer la URL pública del puerto $puerto. Revisa $logErr"
    } else {
        Write-Host "  $puerto -> $url" -ForegroundColor Green
        $urls["$puerto"] = $url
    }
}

$pids | Set-Content -LiteralPath $archivoPids -Encoding ASCII

if ($urls.Count -eq 0) {
    Write-Warning "No se abrió ningún túnel."
    return
}

($urls | ConvertTo-Json) | Set-Content -LiteralPath $archivoJson -Encoding UTF8

Write-Host ""
Write-Host "Config Var para Heroku (Settings > Config Vars):" -ForegroundColor Cyan
Write-Host "A2A_SERVIDORES=$($urls.Values -join ',')"
Write-Host ""
Write-Host "Mapa puerto -> URL guardado en logs/tuneles.json"
Write-Host "Aviso: la URL cambia cada vez que se reinicia el túnel."
Write-Host "Cierra todo con: .\scripts\tuneles_agentes.ps1 -Detener"
