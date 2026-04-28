@echo off
REM FlavorSnap Backup Script (Windows Version)
REM Automated backup system for data and model files
REM Author: FlavorSnap Team
REM Version: 1.0.0

setlocal enabledelayedexpansion

REM Configuration
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set BACKUP_DIR=%PROJECT_ROOT%\backups
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_NAME=flavorsnap_backup_%TIMESTAMP%
set LOG_FILE=%BACKUP_DIR%\backup_%TIMESTAMP%.log

REM Create backup directory
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Logging function
goto :main

:log
echo [%date% %time%] %~1
echo [%date% %time%] %~1 >> "%LOG_FILE%"
goto :eof

:error_exit
call :log "ERROR: %~1"
exit /b 1

REM Check dependencies
:check_dependencies
call :log "Checking dependencies..."

REM Check if 7-Zip is available
where 7z >nul 2>&1
if %errorlevel% neq 0 (
    call :error_exit "7-Zip is required but not found. Please install 7-Zip."
)

REM Check if robocopy is available
where robocopy >nul 2>&1
if %errorlevel% neq 0 (
    call :error_exit "robocopy is required but not found."
)

call :log "All dependencies are available"
goto :eof

REM Create backup directory structure
:create_backup_structure
call :log "Creating backup directory structure..."

set backup_path=%BACKUP_DIR%\%BACKUP_NAME%
mkdir "%backup_path%\models" 2>nul
mkdir "%backup_path%\dataset" 2>nul
mkdir "%backup_path%\uploads" 2>nul
mkdir "%backup_path%\config" 2>nul
mkdir "%backup_path%\scripts" 2>nul
mkdir "%backup_path%\database" 2>nul
mkdir "%backup_path%\logs" 2>nul

echo %backup_path%
goto :eof

REM Backup model files
:backup_models
set backup_path=%~1
call :log "Backing up model files..."

if exist "%PROJECT_ROOT%\model.pth" (
    copy "%PROJECT_ROOT%\model.pth" "%backup_path%\models\" >nul
    call :log "Copied model.pth"
) else (
    call :log "WARNING: model.pth not found"
)

if exist "%PROJECT_ROOT%\food_classes.txt" (
    copy "%PROJECT_ROOT%\food_classes.txt" "%backup_path%\models\" >nul
    call :log "Copied food_classes.txt"
) else (
    call :log "WARNING: food_classes.txt not found"
)

if exist "%PROJECT_ROOT%\ml-model-api" (
    xcopy "%PROJECT_ROOT%\ml-model-api\*.py" "%backup_path%\models\" /Y /Q >nul
    call :log "Copied model-related Python files"
)

goto :eof

REM Backup dataset
:backup_dataset
set backup_path=%~1
call :log "Backing up dataset..."

if exist "%PROJECT_ROOT%\dataset" (
    robocopy "%PROJECT_ROOT%\dataset" "%backup_path%\dataset" /E /XD "*.tmp" "*.cache" >nul
    call :log "Backed up dataset directory"
) else (
    call :log "WARNING: dataset directory not found"
)

goto :eof

REM Backup user uploads
:backup_uploads
set backup_path=%~1
call :log "Backing up user uploads..."

if exist "%PROJECT_ROOT%\uploads" (
    robocopy "%PROJECT_ROOT%\uploads" "%backup_path%\uploads" /E /XD "*.tmp" >nul
    call :log "Backed up uploads directory"
) else (
    call :log "WARNING: uploads directory not found"
)

goto :eof

REM Backup configuration files
:backup_config
set backup_path=%~1
call :log "Backing up configuration files..."

if exist "%PROJECT_ROOT%\package.json" copy "%PROJECT_ROOT%\package.json" "%backup_path%\config\" >nul
if exist "%PROJECT_ROOT%\frontend\package.json" copy "%PROJECT_ROOT%\frontend\package.json" "%backup_path%\config\" >nul
if exist "%PROJECT_ROOT%\ml-model-api\requirements.txt" copy "%PROJECT_ROOT%\ml-model-api\requirements.txt" "%backup_path%\config\" >nul
if exist "%PROJECT_ROOT%\Cargo.toml" copy "%PROJECT_ROOT%\Cargo.toml" "%backup_path%\config\" >nul
if exist "%PROJECT_ROOT%\frontend\Cargo.toml" copy "%PROJECT_ROOT%\frontend\Cargo.toml" "%backup_path%\config\" >nul
if exist "%PROJECT_ROOT%\tsconfig.json" copy "%PROJECT_ROOT%\tsconfig.json" "%backup_path%\config\" >nul
if exist "%PROJECT_ROOT%\frontend\tsconfig.json" copy "%PROJECT_ROOT%\frontend\tsconfig.json" "%backup_path%\config\" >nul
if exist "%PROJECT_ROOT%\next.config.ts" copy "%PROJECT_ROOT%\next.config.ts" "%backup_path%\config\" >nul
if exist "%PROJECT_ROOT%\frontend\next.config.ts" copy "%PROJECT_ROOT%\frontend\next.config.ts" "%backup_path%\config\" >nul

call :log "Backed up configuration files"
goto :eof

REM Backup important scripts
:backup_scripts
set backup_path=%~1
call :log "Backing up important scripts..."

if exist "%SCRIPT_DIR%" (
    xcopy "%SCRIPT_DIR%" "%backup_path%\scripts\" /E /Y /Q >nul
    call :log "Backed up scripts directory"
)

for /r "%PROJECT_ROOT%" %%f in (setup.*) do (
    copy "%%f" "%backup_path%\scripts\" >nul
)

if exist "%PROJECT_ROOT%\train_model.ipynb" (
    copy "%PROJECT_ROOT%\train_model.ipynb" "%backup_path%\scripts\" >nul
)

call :log "Backed up scripts and notebooks"
goto :eof

REM Backup database files
:backup_database
set backup_path=%~1
call :log "Backing up database files..."

for /r "%PROJECT_ROOT%" %%f in (*.db *.sqlite *.sqlite3 *.sql) do (
    copy "%%f" "%backup_path%\database\" >nul
)

if exist "%PROJECT_ROOT%\data" (
    robocopy "%PROJECT_ROOT%\data" "%backup_path%\database\data" /E >nul
)

call :log "Backed up database files"
goto :eof

REM Create backup metadata
:create_metadata
set backup_path=%~1
call :log "Creating backup metadata..."

echo { > "%backup_path%\backup_info.json"
echo   "backup_name": "%BACKUP_NAME%", >> "%backup_path%\backup_info.json"
echo   "timestamp": "%TIMESTAMP%", >> "%backup_path%\backup_info.json"
echo   "created_by": "%USERNAME%", >> "%backup_path%\backup_info.json"
echo   "hostname": "%COMPUTERNAME%", >> "%backup_path%\backup_info.json"
echo   "project_root": "%PROJECT_ROOT%", >> "%backup_path%\backup_info.json"
echo   "backup_version": "1.0.0", >> "%backup_path%\backup_info.json"
echo   "total_size_mb": "unknown", >> "%backup_path%\backup_info.json"
echo   "file_count": "unknown" >> "%backup_path%\backup_info.json"
echo } >> "%backup_path%\backup_info.json"

call :log "Created backup metadata"
goto :eof

REM Compress backup
:compress_backup
set backup_path=%~1
call :log "Compressing backup..."

cd /d "%BACKUP_DIR%"
7z a "%BACKUP_NAME%.7z" "%BACKUP_NAME%" >nul

call :log "Backup compressed: %BACKUP_NAME%.7z"

REM Remove uncompressed directory
rmdir /S /Q "%BACKUP_NAME%" 2>nul

echo %BACKUP_DIR%\%BACKUP_NAME%.7z
goto :eof

REM Cleanup old backups
:cleanup_old_backups
set keep_count=%~1
if "%keep_count%"=="" set keep_count=7

call :log "Cleaning up old backups (keeping last %keep_count%)..."

cd /d "%BACKUP_DIR%"
for /f "skip=%keep_count% tokens=*" %%f in ('dir /B /O-D flavorsnap_backup_*.7z 2^>nul') do (
    del "%%f" 2>nul
)

call :log "Cleanup completed"
goto :eof

REM Main backup function
:main
call :log "Starting FlavorSnap backup process..."

set keep_count=7
set skip_cleanup=false

REM Parse command line arguments
:parse_args
if "%~1"=="--keep-count" (
    set keep_count=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--skip-cleanup" (
    set skip_cleanup=true
    shift
    goto parse_args
)
if "%~1"=="--help" (
    echo Usage: %~nx0 [--keep-count N] [--skip-cleanup]
    echo   --keep-count N: Keep last N backups (default: 7)
    echo   --skip-cleanup: Skip cleanup of old backups
    exit /b 0
)
if not "%~1"=="" (
    call :error_exit "Unknown option: %~1"
)

REM Execute backup steps
call :check_dependencies

for /f "delims=" %%i in ('call :create_backup_structure') do set backup_path=%%i

call :backup_models "%backup_path%"
call :backup_dataset "%backup_path%"
call :backup_uploads "%backup_path%"
call :backup_config "%backup_path%"
call :backup_scripts "%backup_path%"
call :backup_database "%backup_path%"

call :create_metadata "%backup_path%"

for /f "delims=" %%i in ('call :compress_backup "%backup_path%"') do set backup_file=%%i

if not "%skip_cleanup%"=="true" (
    call :cleanup_old_backups %keep_count%
)

call :log "Backup completed successfully: %backup_file%"

echo Backup completed: %backup_file%
goto :eof
