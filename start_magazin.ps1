$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$shopPython = $null
foreach ($candidate in @('py', 'python3.14', 'python', 'python3')) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
        try {
            & $command.Source -c 'import sys; assert sys.version_info >= (3, 11)' 2>$null
            if ($LASTEXITCODE -eq 0) { $shopPython = $command.Source; break }
        } catch { }
    }
}
if (-not $shopPython) {
    Write-Host 'Este necesar Python 3.11 sau mai nou. Instaleaza Python, apoi deschide din nou Start Magazin.bat.'
    exit 1
}
& $shopPython (Join-Path $PSScriptRoot 'web_app.py') @args
exit $LASTEXITCODE
