[CmdletBinding()]
param(
    [string[]]$Abis = @("arm64-v8a"),
    [int]$ApiLevel = 21,
    [string]$BuildVersion = "1.0.0",
    [int]$BuildNumber = 1,
    [string]$ProjectName = "pnipu_planner",
    [string]$ProductName = "University Planner",
    [string]$ArtifactName = "pnipu_planner",
    [string]$OrgName = "ru.pnipu",
    [string]$BundleId = "ru.pnipu.planner",
    [string]$Description = "Student planner for PNIPU",
    [string]$OutputDir = "",
    [string]$FletExe = "",
    [switch]$SplitPerAbi,
    [switch]$ClearCache,
    [switch]$SkipNativeBuild,
    [string]$AndroidSigningKeyStore = "",
    [string]$AndroidSigningKeyStorePassword = "",
    [string]$AndroidSigningKeyAlias = "",
    [string]$AndroidSigningKeyPassword = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-ExistingPath {
    param(
        [Parameter(Mandatory = $true)][string]$PathValue,
        [Parameter(Mandatory = $true)][string]$ErrorMessage
    )

    if (!(Test-Path -LiteralPath $PathValue)) {
        throw $ErrorMessage
    }

    return (Resolve-Path -LiteralPath $PathValue).Path
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AppDir = Join-Path $RepoRoot "app"
$NativeBuildScript = Join-Path $PSScriptRoot "build_android_so.ps1"

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $RepoRoot "dist\apk"
}

if ([string]::IsNullOrWhiteSpace($FletExe)) {
    $FletExe = Join-Path $RepoRoot ".venv\Scripts\flet.exe"
}

$AppDir = Resolve-ExistingPath -PathValue $AppDir -ErrorMessage "App directory not found: $AppDir"
$NativeBuildScript = Resolve-ExistingPath -PathValue $NativeBuildScript -ErrorMessage "Native build script not found: $NativeBuildScript"
$FletExe = Resolve-ExistingPath -PathValue $FletExe -ErrorMessage "Flet CLI not found: $FletExe"

if ($BuildNumber -lt 1) {
    throw "BuildNumber must be greater than or equal to 1."
}

if (!(Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
}

if (!$SkipNativeBuild) {
    & $NativeBuildScript -Abis $Abis -ApiLevel $ApiLevel
}

$BuildArgs = @(
    "build",
    "apk",
    $AppDir,
    "--module-name", "main",
    "--output", $OutputDir,
    "--arch"
)

$BuildArgs += $Abis
$BuildArgs += @(
    "--project", $ProjectName,
    "--product", $ProductName,
    "--artifact", $ArtifactName,
    "--org", $OrgName,
    "--bundle-id", $BundleId,
    "--description", $Description,
    "--build-version", $BuildVersion,
    "--build-number", "$BuildNumber",
    "--android-permissions", "INTERNET=true", "POST_NOTIFICATIONS=true",
    "--exclude", "__pycache__", "*.pyc", "*.pyo",
    "--cleanup-app",
    "--cleanup-packages",
    "--compile-app",
    "--compile-packages",
    "--no-rich-output",
    "--yes"
)

if ($SplitPerAbi) {
    $BuildArgs += "--split-per-abi"
}

if ($ClearCache) {
    $BuildArgs += "--clear-cache"
}

if (![string]::IsNullOrWhiteSpace($AndroidSigningKeyStore)) {
    $KeystorePath = Resolve-ExistingPath -PathValue $AndroidSigningKeyStore -ErrorMessage "Android keystore not found: $AndroidSigningKeyStore"
    $BuildArgs += @("--android-signing-key-store", $KeystorePath)
}

if (![string]::IsNullOrWhiteSpace($AndroidSigningKeyStorePassword)) {
    $BuildArgs += @("--android-signing-key-store-password", $AndroidSigningKeyStorePassword)
}

if (![string]::IsNullOrWhiteSpace($AndroidSigningKeyAlias)) {
    $BuildArgs += @("--android-signing-key-alias", $AndroidSigningKeyAlias)
}

if (![string]::IsNullOrWhiteSpace($AndroidSigningKeyPassword)) {
    $BuildArgs += @("--android-signing-key-password", $AndroidSigningKeyPassword)
}

Push-Location $RepoRoot
try {
    & $FletExe @BuildArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Flet APK build failed with exit code ${LASTEXITCODE}."
    }
}
finally {
    Pop-Location
}

Get-ChildItem -LiteralPath $OutputDir -Recurse -File | Select-Object FullName, Length, LastWriteTime
