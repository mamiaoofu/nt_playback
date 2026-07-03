
$niceBase = "C:\Program Files (x86)\NICE Systems\NICE Player Release 6"
[AppDomain]::CurrentDomain.add_AssemblyResolve({
    param($sender, $args)
    $name = ($args.Name -split ",")[0] + ".dll"
    $path = Join-Path $niceBase $name
    if (Test-Path $path) {
        return [Reflection.Assembly]::LoadFrom($path)
    }
    return $null
}) | Out-Null

$logic = [Reflection.Assembly]::LoadFrom((Join-Path $niceBase "NiceApplications.Playback.MediaServices.Logic.dll"))
$converterType = $logic.GetType("NiceApplications.Playback.MediaServices.Logic.MediaFileConverter", $true)

echo "--- Methods in MediaFileConverter ---"
$converterType.GetMethods() | ForEach-Object {
    $params = $_.GetParameters() | ForEach-Object { $_.ParameterType.Name + " " + $_.Name }
    $paramStr = [string]::Join(", ", $params)
    echo ($_.ReturnType.Name + " " + $_.Name + "(" + $paramStr + ")")
}
