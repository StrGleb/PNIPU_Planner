[CmdletBinding()]
param(
    [string[]]$Abis = @("arm64-v8a", "armeabi-v7a", "x86_64"),
    [int]$ApiLevel = 21,
    [string]$NdkRoot = "C:\Program Files (x86)\Android\AndroidNDK\android-ndk-r27c",
    [string]$CMakeExe = "C:\Program Files\CMake\bin\cmake.exe",
    [string]$NinjaExe = "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
)

$ErrorActionPreference = "Stop"

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

function Resolve-AndroidTriple {
    param([Parameter(Mandatory = $true)][string]$Abi)

    switch ($Abi) {
        "arm64-v8a" { return "aarch64-linux-android" }
        "armeabi-v7a" { return "arm-linux-androideabi" }
        "x86_64" { return "x86_64-linux-android" }
        "x86" { return "i686-linux-android" }
        default { throw "Unsupported ABI: $Abi" }
    }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$NativeRoot = Join-Path $RepoRoot "app\native"
$BuildRoot = Join-Path $RepoRoot "build"
$AndroidBinRoot = Join-Path $NativeRoot "bin\android"
$ToolchainFile = Join-Path $NdkRoot "build\cmake\android.toolchain.cmake"
$LlvmSysrootLibRoot = Join-Path $NdkRoot "toolchains\llvm\prebuilt\windows-x86_64\sysroot\usr\lib"

if (!(Test-Path $CMakeExe)) {
    throw "CMake not found: $CMakeExe"
}
if (!(Test-Path $NinjaExe)) {
    throw "Ninja not found: $NinjaExe"
}
if (!(Test-Path $ToolchainFile)) {
    throw "Android toolchain file not found: $ToolchainFile"
}

New-Item -ItemType Directory -Force -Path $AndroidBinRoot | Out-Null

foreach ($Abi in $Abis) {
    $Triple = Resolve-AndroidTriple -Abi $Abi
    $BuildDir = Join-Path $BuildRoot "android-$Abi"
    $OutputDir = Join-Path $AndroidBinRoot $Abi
    $RuntimeSource = Join-Path $LlvmSysrootLibRoot "$Triple\libc++_shared.so"

    if (!(Test-Path $RuntimeSource)) {
        throw "libc++_shared.so not found for ABI ${Abi}: $RuntimeSource"
    }

    if (Test-Path $BuildDir) {
        Remove-Item -LiteralPath $BuildDir -Recurse -Force
    }

    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

    $ConfigureArgs = @(
        "-S", $NativeRoot,
        "-B", $BuildDir,
        "-G", "Ninja",
        "-DCMAKE_MAKE_PROGRAM=$NinjaExe",
        "-DCMAKE_TOOLCHAIN_FILE=$ToolchainFile",
        "-DANDROID_USE_LEGACY_TOOLCHAIN_FILE=OFF",
        "-DANDROID_ABI=$Abi",
        "-DANDROID_PLATFORM=android-$ApiLevel",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DPLANNER_ANDROID_STL=c++",
        "-DPLANNER_NATIVE_OUTPUT_DIR=$OutputDir"
    )
    Invoke-External -Command $CMakeExe -Arguments $ConfigureArgs

    $BuildArgs = @("--build", $BuildDir, "--config", "Release")
    Invoke-External -Command $CMakeExe -Arguments $BuildArgs
    Copy-Item -LiteralPath $RuntimeSource -Destination (Join-Path $OutputDir "libc++_shared.so") -Force
}

Get-ChildItem -Path $AndroidBinRoot -Recurse -File | Select-Object FullName, Length
