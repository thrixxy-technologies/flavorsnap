# Coverage Report Script for Windows PowerShell
# This script handles Python execution issues on Windows

param(
    [switch]$Verbose
)

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}

function Test-PythonInstallation {
    Write-Log "Testing Python installation..."
    
    # Test different Python executables
    $pythonExecutables = @(
        "python",
        "python3", 
        "py",
        "C:\Python39\python.exe",
        "C:\Python310\python.exe",
        "C:\Python311\python.exe",
        "C:\Python312\python.exe",
        "C:\Program Files\Python39\python.exe",
        "C:\Program Files\Python310\python.exe",
        "C:\Program Files\Python311\python.exe",
        "C:\Program Files\Python312\python.exe"
    )
    
    foreach ($exe in $pythonExecutables) {
        try {
            $result = & $exe --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Found Python: $exe - $result"
                return $exe
            }
        } catch {
            if ($Verbose) {
                Write-Log "Failed to test $exe : $_" "DEBUG"
            }
        }
    }
    
    # Try Windows App Python launcher
    try {
        $result = & python.exe --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Found Windows App Python: python.exe - $result"
            return "python.exe"
        }
    } catch {
        Write-Log "Windows App Python failed: $_" "DEBUG"
    }
    
    throw "No working Python installation found"
}

function Test-Dependencies {
    param([string]$PythonExe)
    
    Write-Log "Testing required dependencies..."
    
    # Test pytest
    try {
        $result = & $PythonExe -m pytest --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "pytest available: $result"
        } else {
            throw "pytest not available"
        }
    } catch {
        Write-Log "pytest test failed: $_" "ERROR"
        Write-Log "Installing pytest and dependencies..."
        & $PythonExe -m pip install pytest pytest-cov
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install pytest"
        }
    }
    
    # Test python-multipart
    try {
        $result = & $PythonExe -c "import multipart" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "python-multipart available"
        } else {
            throw "python-multipart not available"
        }
    } catch {
        Write-Log "python-multipart test failed: $_" "ERROR"
        Write-Log "Installing python-multipart..."
        & $PythonExe -m pip install python-multipart
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install python-multipart"
        }
    }
}

function Run-CoverageReport {
    param([string]$PythonExe)
    
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $testsPath = Join-Path $repoRoot "tests"
    
    if (-not (Test-Path $testsPath)) {
        throw "Tests directory not found: $testsPath"
    }
    
    Write-Log "Running coverage report..."
    Write-Log "Repository root: $repoRoot"
    Write-Log "Tests directory: $testsPath"
    
    $cmd = @(
        $PythonExe,
        "-m", "pytest",
        "-q",
        "-m", "not performance_smoke and not performance_full",
        "--maxfail=1",
        "--durations=15",
        $testsPath,
        "--cov", "src/api",
        "--cov", "src/core.py", 
        "--cov", "src/utils",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=xml:coverage.xml",
        "--cov-fail-under=90"
    )
    
    Write-Log "Command: $($cmd -join ' ')"
    
    try {
        $process = Start-Process -FilePath $cmd[0] -ArgumentList $cmd[1..($cmd.Length-1)] -WorkingDirectory $repoRoot -Wait -PassThru -NoNewWindow
        if ($process.ExitCode -eq 0) {
            Write-Log "Coverage report completed successfully!"
        } else {
            Write-Log "Coverage report failed with exit code: $($process.ExitCode)" "ERROR"
            exit $process.ExitCode
        }
    } catch {
        Write-Log "Failed to run coverage report: $_" "ERROR"
        exit 1
    }
}

# Main execution
try {
    Write-Log "Starting coverage report..."
    
    $pythonExe = Test-PythonInstallation
    Test-Dependencies $pythonExe
    Run-CoverageReport $pythonExe
    
    Write-Log "Coverage report completed successfully!"
} catch {
    Write-Log "Coverage report failed: $_" "ERROR"
    exit 1
}
