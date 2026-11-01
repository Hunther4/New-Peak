#Requires -Version 5.1
<#
.SYNOPSIS
    Peak Practice - Cloudflare Tunnel HTTPS Launcher.

.DESCRIPTION
    Exposes the local Peak instance to the internet via Cloudflare Quick Tunnel.
    Generates a secure HTTPS link (e.g., https://<id>.trycloudflare.com)
    with zero configuration, no router port forwarding, and automatic SSL.
    Perfect for sharing with family and friends on mobile devices via WhatsApp.

.PARAMETER Port
    Local port to tunnel. Defaults to 7700 (Vite dev server with API proxy).
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 65535)][int]$Port = 7700
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Write-Tunnel {
    param([string]$Message, [string]$Color = 'Cyan')
    Write-Host "[Peak Tunnel] $Message" -ForegroundColor $Color
}

# 1. Locate cloudflared.exe
$cloudflaredCmd = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($null -ne $cloudflaredCmd) {
    $cloudflaredExe = $cloudflaredCmd.Source
} elseif (Test-Path "C:\Program Files (x86)\cloudflared\cloudflared.exe") {
    $cloudflaredExe = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
} elseif (Test-Path "C:\Program Files\cloudflared\cloudflared.exe") {
    $cloudflaredExe = "C:\Program Files\cloudflared\cloudflared.exe"
} else {
    Write-Tunnel "ERROR: No se encontró cloudflared.exe en el sistema." 'Red'
    exit 1
}

# 2. Check if local service is running on port
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($null -eq $conn) {
    Write-Tunnel "AVISO: No se detectó ningún servicio escuchando en el puerto $Port." 'Yellow'
    Write-Tunnel "Recuerda iniciar Peak en otra consola con el comando: peak" 'Yellow'
    Write-Host ""
}

Write-Tunnel "Iniciando túnel seguro de Cloudflare hacia http://127.0.0.1:$Port..." 'Green'

$logDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$tunnelLog = Join-Path $logDir "tunnel.log"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $cloudflaredExe
$psi.Arguments = "tunnel --url http://127.0.0.1:$Port --no-autoupdate"
$psi.RedirectStandardError = $true
$psi.RedirectStandardOutput = $false
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$proc = [System.Diagnostics.Process]::Start($psi)
if ($null -eq $proc) {
    Write-Tunnel "ERROR: No se pudo arrancar el proceso de cloudflared." 'Red'
    exit 1
}

$urlFound = $false
$tunnelUrl = ""

Write-Tunnel "Negociando conexión cifrada con Cloudflare Edge..." 'DarkCyan'

try {
    while (-not $proc.HasExited) {
        $line = $proc.StandardError.ReadLine()
        if ($null -ne $line) {
            Add-Content -Path $tunnelLog -Value $line
            if (-not $urlFound -and $line -match '(https://[a-zA-Z0-9-]+\.trycloudflare\.com)') {
                $tunnelUrl = $matches[1]
                $urlFound = $true
                Write-Host ""
                Write-Host "==========================================================================" -ForegroundColor Green
                Write-Host "  🚀 PEAK PAES ONLINE (TÚNEL HTTPS ACTIVO)                               " -ForegroundColor Green
                Write-Host "==========================================================================" -ForegroundColor Green
                Write-Host "  Enlace seguro para celulares (copia y envía por WhatsApp):" -ForegroundColor White
                Write-Host ""
                Write-Host "  👉 $tunnelUrl" -ForegroundColor Yellow
                Write-Host ""
                Write-Host "  - Certificado SSL: Válido y automático (HTTPS)" -ForegroundColor DarkGray
                Write-Host "  - Compatible con PWA ('Agregar a pantalla de inicio')" -ForegroundColor DarkGray
                Write-Host "  - Presiona Ctrl + C en esta consola para cerrar el túnel" -ForegroundColor DarkGray
                Write-Host "==========================================================================" -ForegroundColor Green
                Write-Host ""
            }
        }
    }
}
finally {
    if ($null -ne $proc -and -not $proc.HasExited) {
        Write-Tunnel "Cerrando túnel de Cloudflare..." 'Yellow'
        $proc.Kill()
    }
}
