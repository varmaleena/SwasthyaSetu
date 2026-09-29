param([ValidateSet('api','web','test','evaluate','build')][string]$Task='api')
$ErrorActionPreference='Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$python=Join-Path (Get-Location) '.venv/Scripts/python.exe'
if($Task -eq 'api') {
    $env:STATE_A_DATABASE_URL='postgresql+psycopg://demo:local-development-only@127.0.0.1:55432/state_a'
    $env:STATE_B_DATABASE_URL='postgresql+psycopg://demo:local-development-only@127.0.0.1:55432/state_b'
    $env:ALLOWED_ORIGINS='http://localhost:5173,http://localhost:4173'
    & $python -m scripts.migrate
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
    & $python -m data.generate
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
    & $python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000
} elseif($Task -eq 'web') { npm.cmd --prefix apps/web run dev }
elseif($Task -eq 'test') { & $python -m pytest -q --basetemp=tmp/pytest-local -p no:cacheprovider }
elseif($Task -eq 'evaluate') {
    & $python -m scripts.evaluate
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
    & $python -m scripts.transport_evaluation
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
    & $python -m scripts.federation_check
} elseif($Task -eq 'build') { npm.cmd --prefix apps/web run build }
exit $LASTEXITCODE
