param(
    [Parameter(Mandatory)][ValidateSet('msi','nsis')][string]$Kind,
    [Parameter(Mandatory)][ValidateSet('clean','upgrade')][string]$Scenario
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') {
    throw 'Run only on a disposable Windows Actions runner, never a user machine.'
}
$candidateDir = (Resolve-Path candidate-assets).Path
$manifest = Get-Content (Join-Path $candidateDir 'candidate.json') -Raw | ConvertFrom-Json
if ($manifest.version -ne '1.2.1' -or $manifest.baseline -ne 'v1.2.0') { throw 'Unexpected candidate versions' }
if (-not $manifest.candidate_only -or $manifest.source_sha -ne (git rev-parse HEAD)) { throw 'Candidate source provenance mismatch' }
$pattern = if ($Kind -eq 'msi') { '*.msi' } else { '*-setup.exe' }

function Get-VerifiedInstaller([string]$Directory) {
    $files = @(Get-ChildItem -LiteralPath $Directory -File -Filter $pattern)
    if ($files.Count -ne 1) { throw "Expected one $Kind installer" }
    $file = $files[0]
    $lines = @(Get-Content (Join-Path $Directory 'SHA256SUMS.txt') | Where-Object {
        $_ -match ('^[a-fA-F0-9]{64}\s+\*?' + [regex]::Escape($file.Name) + '$')
    })
    if ($lines.Count -ne 1) { throw "Expected one exact checksum for $($file.Name)" }
    $expected = ($lines[0] -split '\s+')[0]
    if ((Get-FileHash $file.FullName -Algorithm SHA256).Hash -ne $expected) { throw 'Installer checksum mismatch' }
    return $file.FullName
}

function Invoke-Install([string]$Installer, [string]$Label) {
    if ($Kind -eq 'msi') {
        $process = Start-Process msiexec.exe -ArgumentList "/i `"$Installer`" /qn /norestart /l*v `"$Label-install.log`"" -Wait -PassThru
    } else {
        $process = Start-Process $Installer -ArgumentList '/S' -Wait -PassThru
    }
    if ($process.ExitCode -notin @(0,3010)) { throw "$Label installation failed: $($process.ExitCode)" }
}

function Find-App {
    $roots = @((Join-Path $env:LOCALAPPDATA 'Tolly'), (Join-Path $env:ProgramFiles 'Tolly'), (Join-Path ${env:ProgramFiles(x86)} 'Tolly'))
    $apps = @($roots | Where-Object { Test-Path $_ } | ForEach-Object {
        Get-ChildItem -LiteralPath $_ -Recurse -File -Filter 'tolly-windows.exe'
    })
    if ($apps.Count -ne 1) { throw "Expected exactly one installed app, found $($apps.Count)" }
    return $apps[0]
}

function Test-Launch([string]$AppPath) {
    $savedPath = $env:PATH
    $process = $null
    try {
        $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
        $process = Start-Process $AppPath -PassThru
        Start-Sleep -Seconds 8
        $process.Refresh()
        if ($process.HasExited) { throw "App exited during launch: $($process.ExitCode)" }
    } finally {
        if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
        $env:PATH = $savedPath
    }
}

$candidate = Get-VerifiedInstaller $candidateDir
$installedPackage = $null
$app = $null
$markers = @{}
try {
    if ($Scenario -eq 'upgrade') {
        New-Item -ItemType Directory -Path baseline-assets | Out-Null
        gh release download v1.2.0 --repo $env:GITHUB_REPOSITORY --dir baseline-assets --pattern $pattern --pattern SHA256SUMS.txt
        if ($LASTEXITCODE -ne 0) { throw 'Baseline download failed' }
        $baseline = Get-VerifiedInstaller (Resolve-Path baseline-assets).Path
        Invoke-Install $baseline 'baseline'
        $installedPackage = $baseline
        $app = Find-App
        if ($app.VersionInfo.ProductVersion -notmatch '^1\.2\.0(?:\.0)?$') { throw 'Installed baseline is not 1.2.0' }
        Test-Launch $app.FullName
        # This is the real app_config_dir contract, with synthetic settings only.
        $config = Join-Path $env:APPDATA 'app.tolly.windows'
        $localData = Join-Path $env:LOCALAPPDATA 'app.tolly.windows'
        New-Item -ItemType Directory -Force -Path $config,$localData | Out-Null
        $settings = Join-Path $config 'settings.json'
        '{"hidden_tools":["synthetic-maintenance-tool"],"refresh_seconds":60,"qwenwork_quota_enabled":false}' | Set-Content -LiteralPath $settings -Encoding utf8NoBOM
        $sentinel = Join-Path $localData 'candidate-upgrade-synthetic.txt'
        'synthetic-upgrade-preservation-check' | Set-Content -LiteralPath $sentinel -Encoding utf8NoBOM
        foreach ($path in @($settings,$sentinel)) { $markers[$path] = (Get-FileHash $path -Algorithm SHA256).Hash }
    }
    Invoke-Install $candidate 'candidate'
    $installedPackage = $candidate
    $app = Find-App
    if ($app.VersionInfo.ProductVersion -notmatch '^1\.2\.1(?:\.0)?$') { throw 'Installed app is not candidate 1.2.1' }
    if ((Get-FileHash $app.FullName -Algorithm SHA256).Hash -ne $manifest.app_sha256) { throw 'Installed binary does not match candidate build' }
    $sidecars = @(Get-ChildItem $app.DirectoryName -Recurse -File -Filter 'tally-engine*.exe')
    if ($sidecars.Count -ne 1 -or (Get-FileHash $sidecars[0].FullName -Algorithm SHA256).Hash -ne $manifest.sidecar_sha256) {
        throw 'Installed sidecar does not match candidate build'
    }
    foreach ($path in $markers.Keys) {
        if (-not (Test-Path $path) -or (Get-FileHash $path -Algorithm SHA256).Hash -ne $markers[$path]) { throw 'Upgrade changed synthetic user data' }
    }
    Test-Launch $app.FullName
    foreach ($path in $markers.Keys) {
        if (-not (Test-Path $path) -or (Get-FileHash $path -Algorithm SHA256).Hash -ne $markers[$path]) { throw 'Candidate launch changed synthetic user data' }
    }
} finally {
    if ($installedPackage) {
        Get-Process tolly-windows -ErrorAction SilentlyContinue | Stop-Process -Force
        $app = Find-App
        if ($Kind -eq 'msi') {
            $uninstall = Start-Process msiexec.exe -ArgumentList "/x `"$installedPackage`" /qn /norestart /l*v candidate-uninstall.log" -Wait -PassThru
        } else {
            $uninstallers = @(Get-ChildItem $app.DirectoryName -File -Filter '*uninstall*.exe')
            if ($uninstallers.Count -ne 1) { throw 'Expected exactly one NSIS uninstaller' }
            $uninstall = Start-Process $uninstallers[0].FullName -ArgumentList '/S' -Wait -PassThru
        }
        if ($uninstall.ExitCode -notin @(0,3010)) { throw "Uninstall failed: $($uninstall.ExitCode)" }
        for ($attempt = 0; $attempt -lt 30 -and (Test-Path $app.FullName); $attempt++) { Start-Sleep -Seconds 1 }
        if (Test-Path $app.FullName) { throw 'App executable remained after uninstall' }
    }
}
"PASS: $Kind $Scenario; checksums, installed binary, launch, data checks and uninstall"
