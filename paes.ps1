#Requires -Version 5.1
<#
.SYNOPSIS
    Peak Practice - Windows launcher.

.DESCRIPTION
    Starts the FastAPI backend (uvicorn) and the Vite frontend, waits until both
    actually answer HTTP requests, and only then opens the browser.

    Everything is resolved relative to this script, so the repository can live
    anywhere on disk. Service output is appended to <repo>\logs\backend.log and
    <repo>\logs\frontend.log.

.PARAMETER BackendPort
    TCP port used by the backend. Defaults to 8000.

.PARAMETER FrontendPort
    TCP port used by the Vite dev server. Defaults to 7700.

.PARAMETER ReadyTimeoutSeconds
    Maximum time to wait for each service to answer HTTP. Defaults to 90.

.PARAMETER NoBrowser
    Do not open the browser once both services are ready. Useful for automated
    runs and for verification on non-default ports.
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 65535)][int]$BackendPort = 8000,
    [ValidateRange(1, 65535)][int]$FrontendPort = 7700,
    [ValidateRange(5, 600)][int]$ReadyTimeoutSeconds = 90,
    [switch]$NoBrowser
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

# --- Paths -------------------------------------------------------------------
# $PSScriptRoot keeps the launcher portable: no absolute path is ever hardcoded.
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot 'backend'
$FrontendDir = Join-Path $ProjectRoot 'frontend'
$VenvDir = Join-Path $BackendDir 'venv'
$PythonExe = Join-Path $VenvDir 'Scripts\python.exe'
$LogsDir = Join-Path $ProjectRoot 'logs'
$BackendLogPath = Join-Path $LogsDir 'backend.log'
$FrontendLogPath = Join-Path $LogsDir 'frontend.log'

$BackendUrl = "http://127.0.0.1:$BackendPort/"
$FrontendUrl = "http://127.0.0.1:$FrontendPort/"

$PollIntervalMs = 500
$ReuseGraceSeconds = 15

# --- Helpers -----------------------------------------------------------------

function Write-Peak {
    param([string]$Message, [string]$Color = 'Gray')
    Write-Host "[Peak] $Message" -ForegroundColor $Color
}

function Write-Detail {
    param([string]$Message, [string]$Color = 'DarkGray')
    Write-Host "        $Message" -ForegroundColor $Color
}

function Get-PropertyValue {
    # StrictMode-safe property access: some WMI properties are missing when the
    # owning process cannot be inspected.
    param($Object, [string]$Name)
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Test-PathUnderRoot {
    # True when $Path points at something inside $Root.
    param([string]$Path, [string]$Root)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    $normalizedPath = $Path.Replace('/', '\').TrimEnd('\')
    $normalizedRoot = $Root.Replace('/', '\').TrimEnd('\')
    if ($normalizedRoot.Length -eq 0) { return $false }
    return $normalizedPath.StartsWith($normalizedRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

function Test-CommandLineUnderRoot {
    # True when $CommandLine references a path inside $Root.
    param([string]$CommandLine, [string]$Root)
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $false }
    $normalizedCommandLine = $CommandLine.Replace('/', '\')
    $normalizedRoot = $Root.Replace('/', '\').TrimEnd('\')
    if ($normalizedRoot.Length -eq 0) { return $false }
    return $normalizedCommandLine.IndexOf($normalizedRoot, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
}

function Get-ProcessChain {
    # Returns the process and its ancestors, closest first.
    param([int]$ProcessId, [int]$MaxDepth = 5)
    $chain = New-Object System.Collections.Generic.List[object]
    $currentId = $ProcessId
    for ($depth = 0; $depth -lt $MaxDepth -and $currentId -gt 0; $depth++) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $currentId" -ErrorAction SilentlyContinue
        if ($null -eq $process) { break }
        $chain.Add($process)
        $parentId = [int](Get-PropertyValue $process 'ParentProcessId')
        if ($parentId -le 0) { break }
        $currentId = $parentId
    }
    return $chain
}

function Get-ListeningProcess {
    # Returns the process that owns the listening socket on $Port, or $null.
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $connection) { return $null }
    $ownerId = [int](Get-PropertyValue $connection 'OwningProcess')
    if ($ownerId -le 0) { return $null }
    return Get-CimInstance Win32_Process -Filter "ProcessId = $ownerId" -ErrorAction SilentlyContinue
}

function Test-OwnedByThisRepo {
    # Decides whether the owner of a port belongs to this checkout.
    param($Process, [ValidateSet('backend', 'frontend')][string]$Role)
    if ($null -eq $Process) { return $false }
    $ownerId = [int](Get-PropertyValue $Process 'ProcessId')
    if ($ownerId -le 0) { return $false }

    foreach ($candidate in Get-ProcessChain -ProcessId $ownerId) {
        $executablePath = [string](Get-PropertyValue $candidate 'ExecutablePath')
        $commandLine = [string](Get-PropertyValue $candidate 'CommandLine')

        if ($Role -eq 'backend') {
            # Our backend runs from the repository virtualenv. On Windows the
            # venv launcher spawns the base interpreter as a child, so the socket
            # owner is often <python>\python.exe while the venv entry point is
            # its parent. The ancestor chain must be inspected as well.
            if (Test-PathUnderRoot -Path $executablePath -Root $VenvDir) { return $true }
            if (($commandLine -like '*uvicorn*') -and
                (Test-CommandLineUnderRoot -CommandLine $commandLine -Root $BackendDir)) { return $true }
        }
        else {
            # Our frontend runs Vite from <repo>\frontend, so the resolved script
            # path inside the command line points at this checkout.
            if (Test-CommandLineUnderRoot -CommandLine $commandLine -Root $FrontendDir) { return $true }
            if (($commandLine -like '*vite*') -and
                (Test-CommandLineUnderRoot -CommandLine $commandLine -Root $ProjectRoot)) { return $true }
        }
    }
    return $false
}

function Get-PortState {
    # Returns a hashtable: State = 'free' | 'ours' | 'foreign', plus Process.
    param([int]$Port, [ValidateSet('backend', 'frontend')][string]$Role)
    $process = Get-ListeningProcess -Port $Port
    if ($null -eq $process) {
        return @{ State = 'free'; Process = $null; ProcessId = 0 }
    }
    $state = 'foreign'
    if (Test-OwnedByThisRepo -Process $process -Role $Role) { $state = 'ours' }
    return @{
        State = $state
        Process = $process
        ProcessId = [int](Get-PropertyValue $process 'ProcessId')
    }
}

function Write-PortConflict {
    # Reports a port held by a process that does not belong to this repository.
    param([int]$Port, [string]$Role, $Process)
    $ownerId = [int](Get-PropertyValue $Process 'ProcessId')
    $name = [string](Get-PropertyValue $Process 'Name')
    $commandLine = [string](Get-PropertyValue $Process 'CommandLine')
    $executablePath = [string](Get-PropertyValue $Process 'ExecutablePath')

    Write-Peak "ERROR: el puerto $Port ya lo ocupa un proceso AJENO a este repositorio." 'Red'
    Write-Detail "Rol esperado : $Role" 'Red'
    Write-Detail "PID          : $ownerId" 'Red'
    Write-Detail "Proceso      : $name" 'Red'
    Write-Detail "Ejecutable   : $executablePath" 'Red'
    Write-Detail "Comando      : $commandLine" 'Red'
    Write-Peak "No se detuvo ese proceso. Libera el puerto $Port y vuelve a ejecutar el launcher." 'Red'
}

function Test-HttpEndpointReady {
    # A 2xx/3xx answer means ready. Any HTTP answer (even 4xx/5xx) also proves
    # the server is listening and serving, so it is accepted as well.
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri $Url -ErrorAction Stop
        $statusCode = [int](Get-PropertyValue $response 'StatusCode')
        return ($statusCode -ge 200 -and $statusCode -lt 400)
    }
    catch {
        $exception = $_.Exception
        if ($exception -is [System.Net.WebException]) {
            if ($null -ne $exception.Response) { return $true }
        }
        return $false
    }
}

function Wait-ForEndpointReady {
    # Polls the endpoint until it answers or the timeout expires.
    param([string]$Url, [int]$TimeoutSeconds)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpEndpointReady -Url $Url) { return $true }
        Start-Sleep -Milliseconds $PollIntervalMs
    }
    return $false
}

function Write-LogTail {
    param([string]$LogPath, [int]$Lines = 20)
    if (-not (Test-Path -LiteralPath $LogPath)) {
        Write-Detail "(no existe el log: $LogPath)"
        return
    }
    $tail = @(Get-Content -LiteralPath $LogPath -Tail $Lines -ErrorAction SilentlyContinue)
    if ($tail.Count -eq 0) {
        Write-Detail "(el log esta vacio: $LogPath)"
        return
    }
    Write-Detail "--- ultimas lineas de $LogPath ---"
    foreach ($line in $tail) { Write-Detail $line }
    Write-Detail "--- fin del log ---"
}

function Write-ReadinessFailure {
    param([string]$Label, [string]$Url, [string]$LogPath, [int]$TimeoutSeconds)
    Write-Peak "ERROR: $Label no respondio en $Url tras $TimeoutSeconds s." 'Red'
    Write-Peak "Revisa el log: $LogPath" 'Red'
    Write-LogTail -LogPath $LogPath
}

function Resolve-PnpmPath {
    # Start-Process may fail when pnpm.cmd is not on the child PATH, so the real
    # path is resolved first and the literal name is only a fallback.
    $command = Get-Command 'pnpm.cmd' -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        $source = [string](Get-PropertyValue $command 'Source')
        if (-not [string]::IsNullOrWhiteSpace($source)) { return $source }
    }
    return 'pnpm.cmd'
}

function Start-LoggedService {
    # Launches a process and merges stdout+stderr into a single appending log.
    #
    # cmd.exe is used as the wrapper for two reasons: Start-Process refuses to
    # redirect stdout and stderr to the same file, and the shell redirection
    # appends to the log instead of truncating it. The trailing double quote is
    # required by the cmd.exe /c parsing rules.
    param(
        [string]$FilePath,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [string]$LogPath
    )
    $command = "`"$FilePath`" $Arguments >> `"$LogPath`" 2>&1"
    $commandLine = '/c "' + $command + '"'
    return Start-Process -FilePath $env:ComSpec -ArgumentList $commandLine `
        -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru
}

# --- Preflight ---------------------------------------------------------------

Write-Peak 'Iniciando entorno de estudio PAES...' 'Cyan'
Write-Detail "Raiz del proyecto : $ProjectRoot"

if (-not (Test-Path -LiteralPath $BackendDir -PathType Container)) {
    Write-Peak "ERROR: no existe el directorio del backend: $BackendDir" 'Red'
    exit 1
}
if (-not (Test-Path -LiteralPath $FrontendDir -PathType Container)) {
    Write-Peak "ERROR: no existe el directorio del frontend: $FrontendDir" 'Red'
    exit 1
}
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    Write-Peak "ERROR: no existe el interprete del entorno virtual: $PythonExe" 'Red'
    exit 1
}

New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
Write-Detail "Log backend       : $BackendLogPath"
Write-Detail "Log frontend      : $FrontendLogPath"

$PnpmPath = Resolve-PnpmPath
Write-Detail "pnpm              : $PnpmPath"

# --- Port inspection ---------------------------------------------------------
# Both ports are inspected before anything is started, so a conflict never
# leaves a half-launched stack behind.

$backendPort = Get-PortState -Port $BackendPort -Role 'backend'
$frontendPort = Get-PortState -Port $FrontendPort -Role 'frontend'

if ($backendPort.State -eq 'foreign') {
    Write-PortConflict -Port $BackendPort -Role 'backend' -Process $backendPort.Process
    exit 1
}
if ($frontendPort.State -eq 'foreign') {
    Write-PortConflict -Port $FrontendPort -Role 'frontend' -Process $frontendPort.Process
    exit 1
}

# --- Backend -----------------------------------------------------------------

$backendStarted = $false
if ($backendPort.State -eq 'ours') {
    Write-Peak "Backend ya activo en puerto $BackendPort (PID $($backendPort.ProcessId))." 'Green'
    if (-not (Wait-ForEndpointReady -Url $BackendUrl -TimeoutSeconds $ReuseGraceSeconds)) {
        Write-Peak "ERROR: el puerto $BackendPort lo ocupa un proceso de este repositorio (PID $($backendPort.ProcessId)) pero no responde." 'Red'
        Write-Peak "Revisa el log: $BackendLogPath" 'Red'
        Write-LogTail -LogPath $BackendLogPath
        exit 1
    }
}
else {
    $backendArguments = "-m uvicorn main:app --host 127.0.0.1 --port $BackendPort --reload"
    $backendProcess = Start-LoggedService -FilePath $PythonExe -Arguments $backendArguments `
        -WorkingDirectory $BackendDir -LogPath $BackendLogPath
    $backendStarted = $true
    Write-Peak "Backend uvicorn lanzado en puerto $BackendPort (PID $($backendProcess.Id))." 'Yellow'
    Write-Detail "Log: $BackendLogPath"
}

# --- Frontend ----------------------------------------------------------------

$frontendStarted = $false
if ($frontendPort.State -eq 'ours') {
    Write-Peak "Frontend ya activo en puerto $FrontendPort (PID $($frontendPort.ProcessId))." 'Green'
    if (-not (Wait-ForEndpointReady -Url $FrontendUrl -TimeoutSeconds $ReuseGraceSeconds)) {
        Write-Peak "ERROR: el puerto $FrontendPort lo ocupa un proceso de este repositorio (PID $($frontendPort.ProcessId)) pero no responde." 'Red'
        Write-Peak "Revisa el log: $FrontendLogPath" 'Red'
        Write-LogTail -LogPath $FrontendLogPath
        exit 1
    }
}
else {
    # --strictPort makes Vite fail loudly instead of silently choosing another
    # port, so the probe below always targets the port that was requested.
    $frontendArguments = "run dev -- --port $FrontendPort --strictPort"
    $frontendProcess = Start-LoggedService -FilePath $PnpmPath -Arguments $frontendArguments `
        -WorkingDirectory $FrontendDir -LogPath $FrontendLogPath
    $frontendStarted = $true
    Write-Peak "Frontend Vite lanzado en puerto $FrontendPort (PID $($frontendProcess.Id))." 'Yellow'
    Write-Detail "Log: $FrontendLogPath"
}

# --- Readiness ---------------------------------------------------------------

if ($backendStarted) {
    if (-not (Wait-ForEndpointReady -Url $BackendUrl -TimeoutSeconds $ReadyTimeoutSeconds)) {
        Write-ReadinessFailure -Label 'Backend' -Url $BackendUrl -LogPath $BackendLogPath -TimeoutSeconds $ReadyTimeoutSeconds
        exit 1
    }
}
Write-Peak "Backend listo en $BackendUrl" 'Green'

if ($frontendStarted) {
    if (-not (Wait-ForEndpointReady -Url $FrontendUrl -TimeoutSeconds $ReadyTimeoutSeconds)) {
        Write-ReadinessFailure -Label 'Frontend' -Url $FrontendUrl -LogPath $FrontendLogPath -TimeoutSeconds $ReadyTimeoutSeconds
        exit 1
    }
}
Write-Peak "Frontend listo en $FrontendUrl" 'Green'

# --- Browser -----------------------------------------------------------------

if (-not $NoBrowser) {
    Start-Process $FrontendUrl
    Write-Peak "Plataforma abierta en $FrontendUrl" 'Green'
}
else {
    Write-Peak "Navegador no abierto (-NoBrowser). URL de la plataforma: $FrontendUrl" 'Green'
}

exit 0
