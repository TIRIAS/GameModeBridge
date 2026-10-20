# PC 앱 exe 빌드. 결과물을 저장소 루트의 dist 폴더(배포 폴더, 커밋 제외)에 복사함
# 실행: pc 폴더에서 powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw '테스트 실패로 빌드를 중단함' }

.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --noconsole --name GameModeBridge --paths . `
    --hidden-import pystray._win32 --hidden-import keyring.backends.Windows `
    --icon (Join-Path $PSScriptRoot 'assets\GameModeBridge.ico') `
    --distpath dist --workpath build\pyi --specpath build --log-level WARN gmb\__main__.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller 빌드 실패' }

$out = Join-Path $PSScriptRoot '..\dist'
New-Item -ItemType Directory -Force $out | Out-Null
Copy-Item dist\GameModeBridge.exe $out -Force
Get-Item (Join-Path $out 'GameModeBridge.exe') | Select-Object FullName, Length
