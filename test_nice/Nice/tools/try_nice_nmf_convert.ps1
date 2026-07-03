param(
    [Parameter(Mandatory = $true)]
    [string]$InputNmf,

    [Parameter(Mandatory = $true)]
    [string]$OutputFile,

    [string]$Compression = "PCM"
)

$ErrorActionPreference = "Stop"

$niceBase = "C:\Program Files (x86)\NICE Systems\NICE Player Release 6"

[AppDomain]::CurrentDomain.add_AssemblyResolve({
    param($sender, $args)
    $name = ($args.Name -split ",")[0] + ".dll"
    $path = Join-Path "C:\Program Files (x86)\NICE Systems\NICE Player Release 6" $name
    if (Test-Path $path) {
        return [Reflection.Assembly]::LoadFrom($path)
    }
    return $null
}) | Out-Null

Set-Location $niceBase

$utils = [Reflection.Assembly]::LoadFrom((Join-Path $niceBase "NiceApplications.Playback.Utils.dll"))
$logic = [Reflection.Assembly]::LoadFrom((Join-Path $niceBase "NiceApplications.Playback.MediaServices.Logic.dll"))

$compressionType = $utils.GetType("NiceApplications.Playback.Utils.CompressionType", $true)
$compressionValue = [Enum]::Parse($compressionType, $Compression)

$converterType = $logic.GetType("NiceApplications.Playback.MediaServices.Logic.MediaFileConverter", $true)
$method = $converterType.GetMethod("NmfToVox", [Reflection.BindingFlags] "Public,Static")
$method.Invoke($null, @($InputNmf, $OutputFile, $compressionValue))

$item = Get-Item -LiteralPath $OutputFile
$bytes = [IO.File]::ReadAllBytes($OutputFile)
$prefix = ($bytes[0..([Math]::Min(15, $bytes.Length - 1))] | ForEach-Object { $_.ToString("X2") }) -join " "

[PSCustomObject]@{
    Output = $item.FullName
    Length = $item.Length
    Compression = $Compression
    Prefix = $prefix
}
