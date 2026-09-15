$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Find-Python {
    $candidates = @()
    foreach ($name in @('python', 'python3', 'py')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notmatch 'WindowsApps\\python') { $candidates += $command.Source }
    }
    $candidates += @(Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    foreach ($candidate in $candidates) {
        $found = & $candidate -c 'import sys; print(sys.executable) if sys.version_info >= (3,11) else sys.exit(1)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { return ($found | Select-Object -Last 1) }
    }
    return $null
}
function Install-Package($id) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'Manca WinGet: installa/aggiorna App Installer dal Microsoft Store, poi riapri Avvia_Dashboard.bat.'
    }
    Write-Host "Installazione automatica di $id ..."
    & winget install --id $id --exact --source winget --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Installazione di $id non riuscita. Controlla connessione e autorizzazioni Windows." }
    Refresh-Path
}
try {
    $python = Find-Python
    if (-not $python) {
        Install-Package 'Python.Python.3.12'
        $python = Find-Python
    }
    if (-not $python) { throw "Python non trovato dopo l'installazione. Chiudi e riapri il launcher." }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        try { Install-Package 'Git.Git' }
        catch { Write-Warning "Git non disponibile: sincronizzazione disabilitata, dashboard utilizzabile. $_" }
    }
    & $python (Join-Path $PSScriptRoot 'avvia_dashboard.py')
    exit $LASTEXITCODE
} catch {
    Write-Host "Avvio non riuscito: $_" -ForegroundColor Red
    exit 1
}
