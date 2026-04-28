# FlavorSnap Docker Deployment Script (PowerShell)
# This script handles the complete Docker deployment process

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("production", "development")]
    [string]$Environment,
    
    [Parameter(Mandatory=$true)]
    [ValidateSet("build", "start", "stop", "restart", "logs", "status", "cleanup", "full")]
    [string]$Command
)

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    White = "White"
}

# Functions
function Write-LogInfo {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Green
}

function Write-LogWarn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor $Colors.Yellow
}

function Write-LogError {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

function Test-Prerequisites {
    Write-LogInfo "Checking prerequisites..."
    
    # Check if Docker is installed
    try {
        $null = Get-Command docker -ErrorAction Stop
        Write-LogInfo "Docker is installed"
    }
    catch {
        Write-LogError "Docker is not installed. Please install Docker Desktop first."
        exit 1
    }
    
    # Check if Docker Compose is installed
    try {
        $null = Get-Command docker-compose -ErrorAction Stop
        Write-LogInfo "Docker Compose is installed"
    }
    catch {
        Write-LogError "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    }
    
    # Check if model file exists
    if (-not (Test-Path "model.pth")) {
        Write-LogWarn "Model file 'model.pth' not found. Please ensure it's in the project root."
    }
    
    Write-LogInfo "Prerequisites check completed."
}

function Initialize-Environment {
    Write-LogInfo "Setting up environment for $Environment..."
    
    # Copy environment file
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.docker") {
            Copy-Item ".env.docker" ".env"
            Write-LogInfo "Created .env from .env.docker"
        }
        else {
            Write-LogWarn "No .env file found. Creating default configuration."
            @"
BUILD_ENV=production
FRONTEND_PORT=3000
BACKEND_PORT=5000
NEXT_PUBLIC_API_URL=http://backend:5000
NEXT_PUBLIC_MODEL_ENDPOINT=/predict
MODEL_PATH=/app/models/model.pth
UPLOAD_FOLDER=/app/uploads
LOG_LEVEL=INFO
"@ | Out-File -FilePath ".env" -Encoding utf8
        }
    }
    
    # Create necessary directories
    $directories = @(
        "logs/nginx",
        "ml-model-api/uploads", 
        "ml-model-api/logs",
        "nginx/ssl"
    )
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-LogInfo "Environment setup completed."
}

function Build-Images {
    Write-LogInfo "Building Docker images..."
    
    if ($Environment -eq "development") {
        docker-compose -f docker-compose.dev.yml build
    }
    else {
        docker-compose -f docker-compose.yml build
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-LogInfo "Docker images built successfully."
    }
    else {
        Write-LogError "Failed to build Docker images."
        exit 1
    }
}

function Start-Services {
    Write-LogInfo "Starting services..."
    
    if ($Environment -eq "development") {
        docker-compose -f docker-compose.dev.yml up -d
    }
    else {
        docker-compose -f docker-compose.yml up -d
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-LogInfo "Services started successfully."
    }
    else {
        Write-LogError "Failed to start services."
        exit 1
    }
}

function Test-HealthCheck {
    Write-LogInfo "Performing health checks..."
    
    # Wait for services to start
    Start-Sleep -Seconds 10
    
    # Check frontend
    try {
        $frontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "3000" }
        $response = Invoke-WebRequest -Uri "http://localhost:$frontendPort/" -TimeoutSec 5 -ErrorAction Stop
        Write-LogInfo "Frontend is healthy"
    }
    catch {
        Write-LogError "Frontend health check failed: $($_.Exception.Message)"
    }
    
    # Check backend
    try {
        $backendPort = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "5000" }
        $response = Invoke-WebRequest -Uri "http://localhost:$backendPort/health" -TimeoutSec 5 -ErrorAction Stop
        Write-LogInfo "Backend is healthy"
    }
    catch {
        Write-LogError "Backend health check failed: $($_.Exception.Message)"
    }
}

function Show-Status {
    Write-LogInfo "Service status:"
    
    if ($Environment -eq "development") {
        docker-compose -f docker-compose.dev.yml ps
    }
    else {
        docker-compose -f docker-compose.yml ps
    }
}

function Show-Logs {
    Write-LogInfo "Recent logs:"
    
    if ($Environment -eq "development") {
        docker-compose -f docker-compose.dev.yml logs --tail=50
    }
    else {
        docker-compose -f docker-compose.yml logs --tail=50
    }
}

function Invoke-Cleanup {
    Write-LogInfo "Cleaning up old containers and images..."
    
    # Stop and remove containers
    if ($Environment -eq "development") {
        docker-compose -f docker-compose.dev.yml down -v
    }
    else {
        docker-compose -f docker-compose.yml down -v
    }
    
    # Remove unused images
    docker image prune -f
    
    Write-LogInfo "Cleanup completed."
}

# Main execution
switch ($Command) {
    "build" {
        Test-Prerequisites
        Initialize-Environment
        Build-Images
    }
    "start" {
        Test-Prerequisites
        Initialize-Environment
        Start-Services
        Test-HealthCheck
        Show-Status
    }
    "stop" {
        if ($Environment -eq "development") {
            docker-compose -f docker-compose.dev.yml down
        }
        else {
            docker-compose -f docker-compose.yml down
        }
        Write-LogInfo "Services stopped."
    }
    "restart" {
        # Stop services
        if ($Environment -eq "development") {
            docker-compose -f docker-compose.dev.yml down
        }
        else {
            docker-compose -f docker-compose.yml down
        }
        
        # Start services
        Test-Prerequisites
        Initialize-Environment
        Start-Services
        Test-HealthCheck
        Show-Status
    }
    "logs" {
        Show-Logs
    }
    "status" {
        Show-Status
    }
    "cleanup" {
        Invoke-Cleanup
    }
    "full" {
        Invoke-Cleanup
        Test-Prerequisites
        Initialize-Environment
        Build-Images
        Start-Services
        Test-HealthCheck
        Show-Status
    }
    default {
        Write-Host "Usage: .\docker-deploy.ps1 -Environment <environment> -Command <command>" -ForegroundColor $Colors.White
        Write-Host ""
        Write-Host "Environments:" -ForegroundColor $Colors.White
        Write-Host "  production    Production deployment with Nginx" -ForegroundColor $Colors.White
        Write-Host "  development   Development deployment" -ForegroundColor $Colors.White
        Write-Host ""
        Write-Host "Commands:" -ForegroundColor $Colors.White
        Write-Host "  build         Build Docker images" -ForegroundColor $Colors.White
        Write-Host "  start         Start services" -ForegroundColor $Colors.White
        Write-Host "  stop          Stop services" -ForegroundColor $Colors.White
        Write-Host "  restart       Restart services" -ForegroundColor $Colors.White
        Write-Host "  logs          Show logs" -ForegroundColor $Colors.White
        Write-Host "  status        Show service status" -ForegroundColor $Colors.White
        Write-Host "  cleanup       Clean up containers and images" -ForegroundColor $Colors.White
        Write-Host "  full          Full deployment (cleanup + build + start)" -ForegroundColor $Colors.White
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor $Colors.White
        Write-Host "  .\docker-deploy.ps1 -Environment production -Command full" -ForegroundColor $Colors.White
        Write-Host "  .\docker-deploy.ps1 -Environment development -Command start" -ForegroundColor $Colors.White
        Write-Host "  .\docker-deploy.ps1 -Environment production -Command logs" -ForegroundColor $Colors.White
        exit 1
    }
}
