Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Настройка структуры проекта nexus_qa..." -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Удаление ненужных файлов (если они есть)
# Если в tree_output.txt были файлы, которые нужно явно стереть, укажите их здесь[cite: 1].
$badFiles = @(
    "old_unused_file.txt"
)

foreach ($file in $badFiles) {
    if (Test-Path $file) {
        Remove-Item -Path $file -Force
        Write-Host "Удален устаревший файл: $file" -ForegroundColor Yellow
    }
}

# 2. Создание структуры директорий
$directories = @(
    "config",
    "src",
    "src\api",
    "src\ui",
    "src\ui\pages",
    "tests",
    "tests\api_tests",
    "tests\ui_tests"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "Создана папка: $dir" -ForegroundColor Green
    }
}

# 3. Создание пустых файлов (БЕЗ перезаписи существующих)
$files = @(
    "config\__init__.py",
    "config\settings.py",
    "src\__init__.py",
    "src\api\__init__.py",
    "src\api\base_client.py",
    "src\ui\__init__.py",
    "src\ui\base_page.py",
    "src\ui\pages\__init__.py",
    "src\ui\pages\login_page.py",
    "src\ui\pages\dashboard_page.py",
    "tests\__init__.py",
    "tests\conftest.py",
    "tests\api_tests\__init__.py",
    "tests\api_tests\test_auth_api.py",
    "tests\ui_tests\__init__.py",
    "tests\ui_tests\test_login_ui.py"
)

foreach ($file in $files) {
    if (-not (Test-Path $file)) {
        New-Item -ItemType File -Path $file | Out-Null
        Write-Host "Создан файл: $file" -ForegroundColor Green
    }
}

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Структура успешно синхронизирована!" -ForegroundColor Green
Write-Host "Существующие файлы (включая .venv и .env) не изменялись." -ForegroundColor White
Write-Host "====================================================" -ForegroundColor Cyan

Read-Host -Prompt "Нажмите Enter для выхода"