$ErrorActionPreference = 'Stop'
$destParent = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $destParent 'LibreOfficePortable'
$tmp = Join-Path $env:TEMP 'LibreOfficePortable_26.2.4_MultilingualStandard.paf.exe'
$url = 'https://downloads.sourceforge.net/portableapps/LibreOfficePortable_26.2.4_MultilingualStandard.paf.exe'
$attendu = '4BDE93374AEF4409243505B20D16561A4628AC7591457DD01FC6E1CCF571BA65'
Write-Host 'Telechargement LibreOffice Portable...'
Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
$hash = (Get-FileHash $tmp -Algorithm SHA256).Hash
if ($hash -ne $attendu) { throw "Empreinte incorrecte : $hash" }
Write-Host "Installation dans $dest"
Start-Process -FilePath $tmp -ArgumentList "/DEST=`"$dest`" /SILENT" -Wait
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
$soffice = Join-Path $dest 'App\libreoffice\program\soffice.exe'
if (-not (Test-Path $soffice)) { throw 'soffice.exe introuvable apres installation' }
Write-Host 'OK'
