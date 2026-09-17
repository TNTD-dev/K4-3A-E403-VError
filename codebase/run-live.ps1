$ErrorActionPreference = "Stop"
$codebaseRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $codebaseRoot "backend"
$frontendRoot = Join-Path $codebaseRoot "frontend"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Chưa có backend/.venv. Chạy: uv sync --extra test trong thư mục backend."
}

$envFile = Join-Path $backendRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath (Join-Path $backendRoot ".env.example") -Destination $envFile
    Write-Host "Đã tạo backend/.env. Hãy dán OPENAI_API_KEY nếu muốn AI thật." -ForegroundColor Yellow
}

$backendPort = 8000
while (Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue) {
    $backendPort += 1
    if ($backendPort -gt 8010) { throw "Không tìm được cổng backend trống trong khoảng 8000-8010." }
}
$backendUrl = "http://127.0.0.1:$backendPort"

$backend = Start-Process -FilePath $python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "$backendPort" `
    -WorkingDirectory $backendRoot `
    -WindowStyle Hidden `
    -PassThru

try {
    Write-Host "Backend: $backendUrl" -ForegroundColor Cyan
    Write-Host "Frontend: http://127.0.0.1:5173" -ForegroundColor Cyan
    $env:VITE_API_BASE = $backendUrl
    Set-Location -LiteralPath $frontendRoot
    npm run dev
}
finally {
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id
    }
}
