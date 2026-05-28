# Planfin Dashboard - Local Server
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Planfin Dashboard - Local Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "กำลังเปิด Dashboard ที่ http://localhost:3000" -ForegroundColor Green
Write-Host "กด Ctrl+C เพื่อปิด Server" -ForegroundColor Yellow
Write-Host ""

Set-Location $PSScriptRoot
Start-Sleep -Seconds 1

# Open browser
Start-Process "http://localhost:3000"

# Start server
python -m http.server 3000
