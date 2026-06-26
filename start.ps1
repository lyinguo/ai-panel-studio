# ============================================================
# AI Panel Studio — 一键启动脚本 (PowerShell)
# 启动后端 FastAPI + 前端 Vite 开发服务器
# ============================================================

$BackendPort = 8000
$FrontendPort = 5173
$BackendDir = Join-Path $PSScriptRoot "backend"
$FrontendDir = Join-Path $PSScriptRoot "frontend"
$CondaEnv = "ai-panel-studio"
$CondaExec = "D:\anaconda\Scripts\conda.exe"
$PythonExec = "D:\anaconda\envs\$CondaEnv\python.exe"

Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      AI Panel Studio — 一键启动             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── 检查 conda 环境 ──
if (-not (Test-Path $PythonExec)) {
    Write-Host "⚠ Conda 环境 '$CondaEnv' 未找到！" -ForegroundColor Yellow
    Write-Host "  请先执行：conda create -n $CondaEnv python=3.11 -y" -ForegroundColor Yellow
    Write-Host "  然后：conda activate $CondaEnv" -ForegroundColor Yellow
    Write-Host "  最后：cd backend && pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Conda 环境: $CondaEnv" -ForegroundColor Green

# ── 检查 .env ──
$EnvFile = Join-Path $PSScriptRoot ".env"
$EnvExample = Join-Path $PSScriptRoot ".env.example"
if (-not (Test-Path $EnvFile)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "⚠ 已从 .env.example 创建 .env，请编辑填入 DEEPSEEK_API_KEY" -ForegroundColor Yellow
}

# ── 安装前端依赖 ──
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "📦 安装前端依赖..." -ForegroundColor Cyan
    Push-Location $FrontendDir
    npm install 2>&1 | Out-Null
    Pop-Location
    Write-Host "✅ 前端依赖已安装" -ForegroundColor Green
}

# ── 启动后端 ──
Write-Host "🚀 启动后端 (端口 $BackendPort)..." -ForegroundColor Cyan
$BackendProcess = Start-Process -WindowStyle Hidden -PassThru -FilePath $PythonExec -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port $BackendPort --reload" -WorkingDirectory $BackendDir
Start-Sleep -Seconds 3
Write-Host "✅ 后端已启动: http://localhost:$BackendPort" -ForegroundColor Green

# ── 健康检查 ──
try {
    $Health = Invoke-WebRequest -Uri "http://localhost:$BackendPort/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "✅ 后端健康检查通过" -ForegroundColor Green
} catch {
    Write-Host "⚠ 后端尚未就绪，等待中..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
}

# ── 启动前端 ──
Write-Host "🚀 启动前端 (端口 $FrontendPort)..." -ForegroundColor Cyan
$FrontendProcess = Start-Process -WindowStyle Hidden -PassThru -FilePath "npx.cmd" -ArgumentList "vite --port $FrontendPort --host 0.0.0.0" -WorkingDirectory $FrontendDir
Start-Sleep -Seconds 4

# ── 打开浏览器 ──
$Url = "http://localhost:$FrontendPort"
Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   🎬 系统已就绪！                           ║" -ForegroundColor Cyan
Write-Host "║                                              ║" -ForegroundColor Cyan
Write-Host "║   前端:  $Url               ║" -ForegroundColor Cyan
Write-Host "║   后端:  http://localhost:$BackendPort               ║" -ForegroundColor Cyan
Write-Host "║                                              ║" -ForegroundColor Cyan
Write-Host "║   按任意键停止所有服务...                    ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan

# 打开默认浏览器
Start-Process $Url

# 等待用户按键停止
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null

# ── 清理 ──
Write-Host "`n🛑 正在停止服务..." -ForegroundColor Yellow
if (-not $BackendProcess.HasExited) { $BackendProcess.Kill() }
if (-not $FrontendProcess.HasExited) { $FrontendProcess.Kill() }
Write-Host "✅ 所有服务已停止" -ForegroundColor Green
