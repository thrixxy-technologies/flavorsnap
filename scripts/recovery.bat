@echo off
REM FlavorSnap Recovery Script (Windows Version)
REM Automated recovery procedures for data and model files
REM Author: FlavorSnap Team
REM Version: 1.0.0

setlocal enabledelayedexpansion

REM Configuration
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set BACKUP_DIR=%PROJECT_ROOT%\backups
set LOG_FILE=%BACKUP_DIR%\recovery_%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log
set LOG_FILE=%LOG_FILE: =0%

REM Colors for output (simplified for Windows)
set RED=[91m
set GREEN=[92m
set YELLOW=[93m
set BLUE=[94m
set NC=[0m

REM Logging functions
goto :main

:log
echo %BLUE%[%date% %time%]%NC% %~1
echo [%date% %time%] %~1 >> "%LOG_FILE%"
goto :eof

:log_success
echo %GREEN%[%date% %time%] SUCCESS:%NC% %~1
echo [%date% %time%] SUCCESS: %~1 >> "%LOG_FILE%"
goto :eof

:log_warning
echo %YELLOW%[%date% %time%] WARNING:%NC% %~1
echo [%date% %time%] WARNING: %~1 >> "%LOG_FILE%"
goto :eof

:log_error
echo %RED%[%date% %time%] ERROR:%NC% %~1
echo [%date% %time%] ERROR: %~1 >> "%LOG_FILE%"
goto :eof

:error_exit
call :log_error "%~1"
exit /b 1

REM Check dependencies
:check_dependencies
call :log "Checking dependencies..."

where 7z >nul 2>&1
if %errorlevel% neq 0 (
    call :error_exit "7-Zip is required but not found. Please install 7-Zip."
)

where robocopy >nul 2>&1
if %errorlevel% neq 0 (
    call :error_exit "robocopy is required but not found."
)

call :log_success "All dependencies are available"
goto :eof

REM List available backups
:list_backups
call :log "Listing available backups..."

if not exist "%BACKUP_DIR%" (
    call :log_error "Backup directory not found: %BACKUP_DIR%"
    exit /b 1
)

set backup_count=0
for %%f in ("%BACKUP_DIR%\flavorsnap_backup_*.7z") do (
    set /a backup_count+=1
)

if %backup_count% equ 0 (
    call :log_warning "No backup files found"
    exit /b 1
)

echo.
echo %BLUE%Available backups:%NC%
set count=0
for /f "delims=" %%f in ('dir /B /O-D "%BACKUP_DIR%\flavorsnap_backup_*.7z" 2^>nul') do (
    set /a count+=1
    for %%A in ("%BACKUP_DIR%\%%f") do (
        set size=%%~zA
        set /a size=!size!/1024/1024
        echo   %GREEN%!count!%NC% %%f (!size!MB)
    )
)
echo.
goto :eof

REM Extract backup
:extract_backup
set backup_file=%~1
set extract_dir=%~2

call :log "Extracting backup: %~nx1"

if not exist "%backup_file%" (
    call :error_exit "Backup file not found: %backup_file%"
)

if not exist "%extract_dir%" mkdir "%extract_dir%"

7z x "%backup_file%" -o"%extract_dir%" >nul
if %errorlevel% neq 0 (
    call :error_exit "Failed to extract backup file"
)

call :log_success "Backup extracted to: %extract_dir%"
goto :eof

REM Create backup of current state before recovery
:create_pre_recovery_backup
call :log "Creating pre-recovery backup..."

set pre_recovery_backup=%BACKUP_DIR%\pre_recovery_%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set pre_recovery_backup=%pre_recovery_backup: =0%
mkdir "%pre_recovery_backup%" 2>nul

REM Backup critical files that might be overwritten
if exist "%PROJECT_ROOT%\model.pth" copy "%PROJECT_ROOT%\model.pth" "%pre_recovery_backup%\" >nul
if exist "%PROJECT_ROOT%\food_classes.txt" copy "%PROJECT_ROOT%\food_classes.txt" "%pre_recovery_backup%\" >nul

REM Backup directories
if exist "%PROJECT_ROOT%\dataset" robocopy "%PROJECT_ROOT%\dataset" "%pre_recovery_backup%\dataset" /E >nul
if exist "%PROJECT_ROOT%\uploads" robocopy "%PROJECT_ROOT%\uploads" "%pre_recovery_backup%\uploads" /E >nul
if exist "%PROJECT_ROOT%\ml-model-api" robocopy "%PROJECT_ROOT%\ml-model-api" "%pre_recovery_backup%\ml-model-api" /E >nul

call :log_success "Pre-recovery backup created: %pre_recovery_backup%"
goto :eof

REM Recover model files
:recover_models
set backup_dir=%~1
set force=%~2

call :log "Recovering model files..."

if exist "%backup_dir%\models\model.pth" (
    if "%force%"=="true" (
        copy "%backup_dir%\models\model.pth" "%PROJECT_ROOT%\" >nul
        call :log_success "Recovered model.pth"
    ) else (
        if not exist "%PROJECT_ROOT%\model.pth" (
            copy "%backup_dir%\models\model.pth" "%PROJECT_ROOT%\" >nul
            call :log_success "Recovered model.pth"
        ) else (
            call :log_warning "model.pth already exists (use --force to overwrite)"
        )
    )
) else (
    call :log_warning "model.pth not found in backup"
)

if exist "%backup_dir%\models\food_classes.txt" (
    if "%force%"=="true" (
        copy "%backup_dir%\models\food_classes.txt" "%PROJECT_ROOT%\" >nul
        call :log_success "Recovered food_classes.txt"
    ) else (
        if not exist "%PROJECT_ROOT%\food_classes.txt" (
            copy "%backup_dir%\models\food_classes.txt" "%PROJECT_ROOT%\" >nul
            call :log_success "Recovered food_classes.txt"
        ) else (
            call :log_warning "food_classes.txt already exists (use --force to overwrite)"
        )
    )
) else (
    call :log_warning "food_classes.txt not found in backup"
)

if exist "%backup_dir%\models" (
    if not exist "%PROJECT_ROOT%\ml-model-api" mkdir "%PROJECT_ROOT%\ml-model-api" 2>nul
    xcopy "%backup_dir%\models\*.py" "%PROJECT_ROOT%\ml-model-api\" /Y /Q >nul
    call :log_success "Recovered model-related Python files"
)

goto :eof

REM Recover dataset
:recover_dataset
set backup_dir=%~1
set force=%~2

call :log "Recovering dataset..."

if not exist "%backup_dir%\dataset" (
    call :log_warning "Dataset not found in backup"
    goto :eof
)

if "%force%"=="true" (
    robocopy "%backup_dir%\dataset" "%PROJECT_ROOT%\dataset" /E >nul
    call :log_success "Dataset recovered successfully"
) else (
    if not exist "%PROJECT_ROOT%\dataset" (
        robocopy "%backup_dir%\dataset" "%PROJECT_ROOT%\dataset" /E >nul
        call :log_success "Dataset recovered successfully"
    ) else (
        call :log_warning "Dataset directory already exists (use --force to overwrite)"
    )
)

goto :eof

REM Recover uploads
:recover_uploads
set backup_dir=%~1
set force=%~2

call :log "Recovering user uploads..."

if not exist "%backup_dir%\uploads" (
    call :log_warning "Uploads not found in backup"
    goto :eof
)

if "%force%"=="true" (
    if not exist "%PROJECT_ROOT%\uploads" mkdir "%PROJECT_ROOT%\uploads" 2>nul
    robocopy "%backup_dir%\uploads" "%PROJECT_ROOT%\uploads" /E >nul
    call :log_success "User uploads recovered successfully"
) else (
    if not exist "%PROJECT_ROOT%\uploads" (
        mkdir "%PROJECT_ROOT%\uploads" 2>nul
        robocopy "%backup_dir%\uploads" "%PROJECT_ROOT%\uploads" /E >nul
        call :log_success "User uploads recovered successfully"
    ) else (
        call :log_warning "Uploads directory already exists (use --force to overwrite)"
    )
)

goto :eof

REM Recover configuration files
:recover_config
set backup_dir=%~1
set force=%~2

call :log "Recovering configuration files..."

if not exist "%backup_dir%\config" (
    call :log_warning "Configuration files not found in backup"
    goto :eof
)

if exist "%backup_dir%\config\package.json" (
    if "%force%"=="true" (
        copy "%backup_dir%\config\package.json" "%PROJECT_ROOT%\" >nul
    ) else (
        if not exist "%PROJECT_ROOT%\package.json" (
            copy "%backup_dir%\config\package.json" "%PROJECT_ROOT%\" >nul
        )
    )
)

if exist "%backup_dir%\config\requirements.txt" (
    if not exist "%PROJECT_ROOT%\ml-model-api" mkdir "%PROJECT_ROOT%\ml-model-api" 2>nul
    if "%force%"=="true" (
        copy "%backup_dir%\config\requirements.txt" "%PROJECT_ROOT%\ml-model-api\" >nul
    ) else (
        if not exist "%PROJECT_ROOT%\ml-model-api\requirements.txt" (
            copy "%backup_dir%\config\requirements.txt" "%PROJECT_ROOT%\ml-model-api\" >nul
        )
    )
)

call :log_success "Configuration recovery completed"
goto :eof

REM Recover scripts
:recover_scripts
set backup_dir=%~1
set force=%~2

call :log "Recovering scripts..."

if not exist "%backup_dir%\scripts" (
    call :log_warning "Scripts not found in backup"
    goto :eof
)

if "%force%"=="true" (
    robocopy "%backup_dir%\scripts" "%SCRIPT_DIR%" /E >nul
    call :log_success "Scripts recovered successfully"
) else (
    dir /B "%SCRIPT_DIR%" >nul 2>&1
    if %errorlevel% neq 0 (
        robocopy "%backup_dir%\scripts" "%SCRIPT_DIR%" /E >nul
        call :log_success "Scripts recovered successfully"
    ) else (
        call :log_warning "Scripts directory already contains files (use --force to overwrite)"
    )
)

goto :eof

REM Recover database files
:recover_database
set backup_dir=%~1
set force=%~2

call :log "Recovering database files..."

if not exist "%backup_dir%\database" (
    call :log_warning "Database files not found in backup"
    goto :eof
)

for %%f in ("%backup_dir%\database\*.db" "%backup_dir%\database\*.sqlite" "%backup_dir%\database\*.sqlite3" "%backup_dir%\database\*.sql") do (
    if exist "%%f" (
        if "%force%"=="true" (
            copy "%%f" "%PROJECT_ROOT%\" >nul
        ) else (
            if not exist "%PROJECT_ROOT%\%%~nxf" (
                copy "%%f" "%PROJECT_ROOT%\" >nul
            )
        )
    )
)

if exist "%backup_dir%\database\data" (
    if "%force%"=="true" (
        if not exist "%PROJECT_ROOT%\data" mkdir "%PROJECT_ROOT%\data" 2>nul
        robocopy "%backup_dir%\database\data" "%PROJECT_ROOT%\data" /E >nul
    ) else (
        if not exist "%PROJECT_ROOT%\data" (
            mkdir "%PROJECT_ROOT%\data" 2>nul
            robocopy "%backup_dir%\database\data" "%PROJECT_ROOT%\data" /E >nul
        )
    )
)

call :log_success "Database recovery completed"
goto :eof

REM Perform recovery
:perform_recovery
set backup_file=%~1
set force=%~2
set recovery_start=%date% %time%

call :log "Starting recovery from: %~nx1"

REM Create temporary extraction directory
set temp_dir=%BACKUP_DIR%\temp_recovery_%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set temp_dir=%temp_dir: =0%
mkdir "%temp_dir%"

REM Extract backup
call :extract_backup "%backup_file%" "%temp_dir%"

REM Find the extracted backup directory
for /d %%d in ("%temp_dir%\flavorsnap_backup_*") do set extracted_backup_dir=%%d

if "%force%"=="true" (
    call :create_pre_recovery_backup
)

REM Perform recovery
call :recover_models "%extracted_backup_dir%" "%force%"
call :recover_dataset "%extracted_backup_dir%" "%force%"
call :recover_uploads "%extracted_backup_dir%" "%force%"
call :recover_config "%extracted_backup_dir%" "%force%"
call :recover_scripts "%extracted_backup_dir%" "%force%"
call :recover_database "%extracted_backup_dir%" "%force%"

REM Cleanup
rmdir /S /Q "%temp_dir%" 2>nul

call :log_success "Recovery process completed"
goto :eof

REM Show help
:show_help
echo FlavorSnap Recovery Script v1.0.0
echo.
echo Usage: %~nx0 [OPTIONS] [BACKUP_FILE]
echo.
echo OPTIONS:
echo   --list              List available backups
echo   --force             Force overwrite existing files
echo   --help              Show this help message
echo.
echo EXAMPLES:
echo   %~nx0 --list                        # List available backups
echo   %~nx0 backup.7z                     # Recover from specific backup
echo   %~nx0 --force backup.7z             # Force overwrite existing files
echo.
goto :eof

REM Main function
:main
set interactive=false
set force=false
set list_only=false
set backup_file=

REM Parse command line arguments
:parse_args
if "%~1"=="--list" (
    set list_only=true
    shift
    goto parse_args
)
if "%~1"=="--force" (
    set force=true
    shift
    goto parse_args
)
if "%~1"=="--help" (
    call :show_help
    exit /b 0
)
if "%~1"=="" (
    goto args_done
)
if "%~1"=="--" (
    shift
    set backup_file=%~1
    goto args_done
)
if "%~1"=="/?" (
    call :show_help
    exit /b 0
)
set backup_file=%~1
shift
goto parse_args

:args_done
REM Check dependencies
call :check_dependencies

REM Handle different modes
if "%list_only%"=="true" (
    call :list_backups
    exit /b %errorlevel%
)

if "%backup_file%"=="" (
    call :log_error "No backup file specified"
    call :show_help
    exit /b 1
)

if not exist "%backup_file%" (
    call :error_exit "Backup file not found: %backup_file%"
)

call :perform_recovery "%backup_file%" "%force%"
goto :eof
