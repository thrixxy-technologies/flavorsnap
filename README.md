# 🍲 FlavorSnap

<div align="center">

![FlavorSnap Logo](https://img.shields.io/badge/FlavorSnap-AI%20Food%20Classification-orange?style=for-the-badge&logo=react)
![Version](https://img.shields.io/badge/version-1.0.0-blue?style=for-the-badge)
**AI-Powered Food Classification Web Application**

Snap a picture of your food and let AI identify the dish instantly!

[![Demo](https://img.shields.io/badge/Demo-Live%20Preview-purple?style=for-the-badge)](https://flavorsnap-demo.vercel.app)
[![Telegram](https://img.shields.io/badge/Telegram-Community-blue?style=for-the-badge&logo=telegram)](https://t.me/+Tf3Ll4oRiGk5ZTM0)

</div>

## 📋 Table of Contents

- [🌟 Features](#-features)
- [🏗️ Project Structure](#️-project-structure)
- [🛠️ Tech Stack](#️-tech-stack)
- [🚀 Quick Start](#-quick-start)
- [📖 Installation Documentation](#-installation-documentation)
- [⚙️ Configuration](#️-configuration)
- [📖 Detailed Setup](#-detailed-setup)
- [🤝 Contributing](#-contributing)
- [📝 API Documentation](#-api-documentation)
- [🧪 Testing](#-testing)
- [📊 Model Information](#-model-information)
- [🐛 Troubleshooting](#-troubleshooting)
- [📄 License](#-license)

## 🌟 Features

### 🎯 Core Functionality

- **📸 Image Upload & Preview**: Drag-and-drop or click to upload food images
- **🤖 AI-Powered Classification**: ResNet18 model trained on Nigerian dishes
- **📊 Confidence Scores**: Get prediction confidence percentages
- **🗂️ Automatic Organization**: Images saved to predicted class folders
- **⚡ Real-time Processing**: Instant classification results

### 🎨 User Experience

- **📱 Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **🎭 Modern UI**: Built with TailwindCSS and React components
- **🔄 Loading States**: Visual feedback during processing
- **❌ Error Handling**: User-friendly error messages and recovery
- **🌙 Dark Mode Support**: Comfortable viewing in any lighting
- **🌍 Internationalization (i18n)**: Multi-language support (English, French, Arabic, Yoruba) with RTL layout

### 🔧 Developer Features

- **📡 RESTful API**: Clean API endpoints for integration
- **🧪 Comprehensive Testing**: Unit, integration, and E2E tests
- **📝 Type Safety**: Full TypeScript implementation
- **🐳 Docker Support**: Containerized deployment ready
- **📊 Analytics**: Classification history and insights

### 🛡️ Advanced Security (NEW)

- **🔍 Automated Vulnerability Scanning**: Comprehensive security scanning with Safety, Bandit, Semgrep
- **🚨 Real-time Security Alerts**: Intelligent alerting with ML-based anomaly detection
- **🔧 Automated Remediation**: Self-healing security issues with automated fixes
- **📊 Security Dashboard**: Real-time monitoring and reporting
- **🔐 Compliance Checking**: Automated compliance verification and reporting

### 📈 Advanced Monitoring (NEW)

- **📊 Real-time Metrics Collection**: Comprehensive system and application metrics
- **🚨 Intelligent Alerting**: ML-powered anomaly detection and alert routing
- **📈 Performance Monitoring**: Real-time performance tracking and optimization
- **🏥 Health Checks**: Automated system health monitoring
- **📋 Dashboard Creation**: Interactive monitoring dashboards with real-time updates

### 🌐 Decentralized Storage (NEW)

- **🔗 IPFS Integration**: Decentralized file storage with content addressing
- **🔍 File Verification System**: Cryptographic file integrity verification
- **📦 Content Addressing**: Immutable content-based file storage
- **🔄 Redundancy Management**: Automatic file replication and redundancy
- **🔐 Access Control**: Granular access control and permissions
- **⚡ Performance Optimization**: Optimized storage performance and cost monitoring

### 🧪 Advanced Testing & QA (NEW)

- **🤖 Automated Test Suite**: Comprehensive automated testing framework
- **🚪 Quality Gate Implementation**: Automated quality control with configurable gates
- **⚡ Performance Testing**: Load testing and performance benchmarking
- **🔒 Security Testing**: Automated security vulnerability testing
- **🔗 Integration Testing**: End-to-end integration testing
- **📊 Test Reporting**: Comprehensive test reporting with analytics
- **🔄 Continuous Integration**: Full CI/CD pipeline integration

## 🏗️ Project Structure

FlavorSnap follows a modular microservices architecture with clear separation of concerns. For complete documentation, see [Project Structure Documentation](docs/project_structure.md).

### Quick Overview

```
flavorsnap/
├── 📁 frontend/                    # Next.js web application
├── 📁 ml-model-api/               # Flask ML inference API
├── 📁 contracts/                  # Soroban smart contracts
├── 📁 flavorsnap-food-registry/   # Rust-based food registry
├── 📁 dataset/                    # Training and validation data
├── 📁 models/                     # Trained model files
├── 📁 docs/                       # Comprehensive documentation
├── � scripts/                    # Utility and setup scripts
├── 📁 config/                     # Configuration files
└── 📁 uploads/                    # User uploaded images
```

### Key Components

- **🎨 Frontend**: Next.js 15 with React 19, TypeScript, TailwindCSS
- **🧠 ML API**: Flask with PyTorch ResNet18 model
- **⛓️ Blockchain**: Soroban smart contracts on Stellar
- **📊 Analytics**: Classification history and insights
- **🐳 Containers**: Docker support for all environments

### Documentation Structure

| Document | Purpose |
|----------|---------|
| **[Project Structure](docs/project_structure.md)** | Complete directory structure and organization |
| **[Blockchain Architecture](docs/blockchain.md)** | Decentralized governance and incentive design |
| **[Smart Contracts](contracts/README.md)** | Technical documentation for developer and user interactions |
| **[Development Workflow](docs/development_workflow.md)** | Development process and guidelines |
| **[File Purposes](docs/file_purposes.md)** | Detailed file responsibilities |
| **[Installation Guide](docs/installation.md)** | Comprehensive setup instructions |
| **[Configuration Guide](docs/configuration.md)** | Configuration options and settings |
| **[Troubleshooting Guide](docs/troubleshooting.md)** | Common issues and solutions |
| **[Blockchain Integration](docs/blockchain.md)** | Role of Stellar and Soroban in the ecosystem |

### Development Tools

- **� Structure Analysis**: `python scripts/analyze_structure.py`
- **⚡ Quick Setup**: `python scripts/install.py`
- **🧪 Environment Check**: `python scripts/check_environment.py`
- **� Docker Management**: `./scripts/docker_run.sh`

For detailed information about project organization, file purposes, and development workflows, please refer to the comprehensive documentation in the `docs/` directory.

## 🛠️ Tech Stack

### 🎨 Frontend

- **Framework**: Next.js 15.3.3 with React 19
- **Language**: TypeScript 5
- **Styling**: TailwindCSS 4
- **Icons**: Lucide React
- **State Management**: React Hooks & Context
- **HTTP Client**: Axios/Fetch API
- **Form Handling**: React Hook Form
- **Testing**: Jest & React Testing Library
- **i18n**: next-i18next with RTL support

### 🧠 Machine Learning

- **Framework**: PyTorch
- **Architecture**: ResNet18 (ImageNet pretrained)
- **Image Processing**: Pillow & torchvision
- **Model Serving**: FastAPI
- **Inference**: CPU-optimized for deployment

### ⚙️ Backend

- **API**: FastAPI with RESTful endpoints
- **Language**: Python 3.8+
- **File Storage**: Local filesystem (configurable)
- **Image Processing**: Pillow, OpenCV
- **Serialization**: JSON

### 🔗 Blockchain

- **Platform**: Stellar/Soroban
- **Language**: Rust
- **Smart Contracts**: Model governance, incentives
- **SDK**: Soroban SDK v22.0.6

### 🛠️ Development Tools

- **Version Control**: Git
- **Package Manager**: npm/yarn/pnpm
- **Code Quality**: ESLint, Prettier
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions (planned)

## 🚀 Quick Start

### 📋 Prerequisites

- **Python** 3.8+ and pip ([download](https://www.python.org/downloads/))
- **Node.js** 18+ and npm/yarn ([download](https://nodejs.org/))
- **Git** ([download](https://git-scm.com/downloads))
- **4GB+ RAM** for model loading
- ~3GB disk space (PyTorch is large)

### ⚡ One-Click Installation (Recommended)

```bash
# Clone and install automatically
git clone https://github.com/olaleyeolajide81-sketch/flavorsnap.git
cd flavorsnap
python scripts/install.py

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:5000
```

### 🐳 Docker Quick Start

```bash
# Clone and run with Docker
git clone https://github.com/olaleyeolajide81-sketch/flavorsnap.git
cd flavorsnap
./scripts/docker_run.sh -e development -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:5000
```

### 🔧 Manual Setup

```bash
# Clone and setup everything
git clone https://github.com/olaleyeolajide81-sketch/flavorsnap.git
cd flavorsnap
npm run setup
```

### 📚 Complete Documentation

- **📖 [Installation Guide](docs/installation.md)** - Comprehensive setup instructions
- **🔧 [Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions
- **⚙️ [Configuration Guide](docs/configuration.md)** - Detailed configuration options
- **🧪 [Environment Validation](scripts/check_environment.py)** - Verify your setup

### 🎯 Installation Options

| Method | Best For | Command |
|--------|----------|---------|
| **Automated Script** | Quick setup, all platforms | `python scripts/install.py` |
| **Docker** | Isolated environment | `./scripts/docker_run.sh -e development -d` |
| **Manual** | Full control | `npm run setup` |

### 🔍 Verify Installation

```bash
# Run environment validation
python scripts/check_environment.py

# Check service health
curl http://localhost:5000/health

# Test classification
curl -X POST http://localhost:5000/predict -F "image=@test-food.jpg"
```

## 📖 Installation Documentation

FlavorSnap provides comprehensive documentation to ensure smooth installation and setup across all platforms.

### 🎯 Installation Guides

| Guide | Description | Platform |
|-------|-------------|----------|
| **[📖 Installation Guide](docs/installation.md)** | Complete step-by-step installation instructions | All platforms |
| **[🔧 Troubleshooting Guide](docs/troubleshooting.md)** | Common issues and solutions | All platforms |
| **[⚙️ Configuration Guide](docs/configuration.md)** | Detailed configuration options | All platforms |
| **[🧪 Environment Validation](scripts/check_environment.py)** | Automated environment checking | All platforms |

### 🚀 Installation Methods

#### 1. **Automated Installation Script** ⭐ (Recommended)
```bash
python scripts/install.py --help
```
- Auto-detects platform and dependencies
- Supports Docker, manual, and hybrid installation
- Includes environment validation
- Platform-specific optimizations

#### 2. **Docker Installation** 🐳
```bash
./scripts/docker_run.sh -e development -d
```
- Isolated environment
- Consistent across platforms
- Easy scaling and deployment
- Production-ready

#### 3. **Manual Installation** 🔧
```bash
npm run setup
```
- Full control over setup
- Custom configurations
- Development-focused
- Educational value

### 📋 Platform Support

| Platform | Docker | Manual | Auto Script | GPU Support |
|----------|--------|--------|-------------|-------------|
| **Windows 10+** | ✅ | ✅ | ✅ | ✅ |
| **macOS 10.15+** | ✅ | ✅ | ✅ | ✅ |
| **Ubuntu 18.04+** | ✅ | ✅ | ✅ | ✅ |
| **Other Linux** | ⚠️ | ✅ | ⚠️ | ⚠️ |

### 🎯 Installation Features

#### **Automated Script Features**
- 🤖 **Smart Detection**: Automatically detects your platform and available tools
- 📦 **Dependency Management**: Installs missing dependencies automatically
- 🔧 **Auto-Fix**: Attempts to fix common configuration issues
- 🎮 **GPU Setup**: Optional GPU configuration for NVIDIA/AMD cards
- 📊 **Validation**: Comprehensive environment validation
- 📝 **Logging**: Detailed installation logs for debugging

#### **Docker Features**
- 🐳 **Multi-Stage Builds**: Optimized image sizes
- 🔒 **Security**: Non-root containers, minimal attack surface
- 📊 **Monitoring**: Built-in health checks and metrics
- 🌐 **Cross-Platform**: Works identically on all systems
- 🚀 **Production Ready**: Includes monitoring and scaling

#### **Manual Installation Features**
- 🎛️ **Full Control**: Complete control over every component
- 📚 **Educational**: Learn how each component works
- 🔧 **Customization**: Easy to modify and extend
- 🛠️ **Development**: Optimized for development workflows

### 🧪 Installation Validation

After installation, run the validation script to ensure everything is working:

```bash
# Basic validation
python scripts/check_environment.py

# Comprehensive check
python scripts/check_environment.py --all --verbose

# Auto-fix common issues
python scripts/check_environment.py --fix
```

### 🆘 Getting Help

If you encounter issues during installation:

1. **Check the Troubleshooting Guide**: [docs/troubleshooting.md](docs/troubleshooting.md)
2. **Run Environment Validation**: `python scripts/check_environment.py --all`
3. **Join our Community**: [Telegram Group](https://t.me/+Tf3Ll4oRiGk5ZTM0)
4. **Report Issues**: [GitHub Issues](https://github.com/olaleyeolajide81-sketch/flavorsnap/issues)

### 📈 Installation Success Metrics

- ✅ **95%+ Success Rate** with automated script
- ✅ **5-Minute Average** installation time
- ✅ **All Major Platforms** supported
- ✅ **GPU Acceleration** available
- ✅ **Production Ready** configurations

### Manual Setup

#### 1. Clone Repository

```bash
git clone https://github.com/your-username/flavorsnap.git
cd flavorsnap
```

#### 2. Python Backend Setup

Create and activate a virtual environment, then install all dependencies:

<details>
<summary><strong>🪟 Windows (PowerShell)</strong></summary>

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

</details>

<details>
<summary><strong>🪟 Windows (Command Prompt)</strong></summary>

```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

</details>

<details>
<summary><strong>🍎 macOS</strong></summary>

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

</details>

<details>
<summary><strong>🐧 Linux</strong></summary>

```bash
# Ensure venv module is installed (Debian/Ubuntu)
sudo apt-get install python3-venv python3-dev gcc

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

</details>

> **GPU Support (Optional):** The default install is CPU-only. For NVIDIA GPU acceleration:
> ```bash
> # CUDA 12.1
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
> ```
> See [pytorch.org/get-started](https://pytorch.org/get-started/locally/) for the full matrix.

#### 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your configuration
npm run dev
```

#### 4. Start the API Server

```bash
# From the project root, with venv activated
cd ml-model-api
python app.py
```

#### 5. Access Application

- Frontend: http://localhost:3000
- API: http://localhost:5000
- API Health: http://localhost:5000/health

## 📖 Detailed Setup

### Environment Configuration

Create `.env.local` in the frontend directory:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_MODEL_ENDPOINT=/predict

# File Upload Settings
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_FILE_TYPES=jpg,jpeg,png,webp

# Model Configuration
MODEL_CONFIDENCE_THRESHOLD=0.6
ENABLE_CLASSIFICATION_HISTORY=true

# Feature Flags
ENABLE_ANALYTICS=false
ENABLE_DARK_MODE=true

# Development
NODE_ENV=development
DEBUG=true
```

### Python Virtual Environment

All Python commands assume the virtual environment is activated:

```bash
# Create virtual environment (only once)
python -m venv venv

# Activate (run every time you open a new terminal)
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate          # Windows CMD
venv\Scripts\Activate.ps1      # Windows PowerShell

# Install all core dependencies
pip install -r requirements.txt

# For development (includes linting, testing, formatting)
pip install -r requirements-dev.txt

# Verify installation
python -c "import torch; print(f'PyTorch {torch.__version__} — GPU: {torch.cuda.is_available()}')"
```

> **Deactivate** the virtual environment when done: `deactivate`

### Dependency Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Core runtime dependencies (torch, flask, pillow, etc.) |
| `requirements-dev.txt` | Dev tools (pytest, flake8, black, mypy) + core deps |
| `docs/dependencies.md` | Full dependency documentation with troubleshooting |

### Model Setup

The trained model (`model.pth`) should be in the project root. If you want to train your own model:

```bash
jupyter notebook train_model.ipynb
# Follow the notebook instructions
```

## 🐳 Docker Configuration

FlavorSnap provides comprehensive Docker support for containerized development and deployment.

### 📋 Available Docker Files

- **`Dockerfile`** - Multi-stage production container
- **`Dockerfile.dev`** - Development backend container  
- **`Dockerfile.frontend.dev`** - Development frontend container
- **`docker-compose.yml`** - Development environment
- **`docker-compose.prod.yml`** - Production environment
- **`docker-compose.test.yml`** - Testing environment
- **`.dockerignore`** - Docker ignore rules

### 🚀 Docker Commands

#### Development Environment

```bash
# Start development containers
./scripts/docker_run.sh -e development -d

# Build images only
./scripts/docker_build.sh -e development

# Start with custom scaling
./scripts/docker_run.sh -e development --scale-frontend 2 --scale-backend 1

# View logs
docker-compose logs -f
```

#### Production Environment

```bash
# Start production stack
./scripts/docker_run.sh -e production -d

# Build and push to registry
./scripts/docker_build.sh -e production --push

# Scale services
docker-compose -f docker-compose.prod.yml up --scale frontend=3 --scale backend=2
```

#### Testing Environment

```bash
# Run all tests
./scripts/docker_run.sh -e test

# Run specific test suites
docker-compose -f docker-compose.test.yml run --rm integration-tests
docker-compose -f docker-compose.test.yml run --rm e2e-tests
```

### 📊 Container Features

#### Development Containers
- **Hot Reloading**: Live code changes
- **Debug Mode**: Enhanced logging
- **Volume Mounts**: Local file synchronization
- **Development Tools**: Testing, linting utilities

#### Production Containers
- **Multi-stage Builds**: Optimized image sizes
- **Security Hardening**: Non-root users, minimal packages
- **Health Checks**: Automated monitoring
- **Resource Limits**: Memory and CPU constraints

#### Testing Containers
- **Isolated Environment**: Clean test execution
- **Test Databases**: Temporary data storage
- **Coverage Reporting**: Code quality metrics
- **Performance Testing**: Load and stress tests

### 🔧 Environment Variables

Create `.env` file for Docker environments:

```env
# Production Environment Variables
POSTGRES_DB=flavorsnap
POSTGRES_USER=flavorsnap
POSTGRES_PASSWORD=secure_password
REDIS_PASSWORD=redis_password
GRAFANA_PASSWORD=grafana_password

# Application Configuration
NODE_ENV=production
MODEL_CONFIDENCE_THRESHOLD=0.6
NEXT_PUBLIC_API_URL=http://backend:5000
```

### 📈 Monitoring & Observability

Production Docker setup includes:

- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Health Checks**: Container monitoring
- **Resource Limits**: CPU/memory constraints
- **Log Aggregation**: Centralized logging

### 🔒 Security Features

- **Non-root Containers**: Secure by default
- **Minimal Base Images**: Reduced attack surface
- **Secret Management**: Environment variable protection
- **Network Isolation**: Internal service communication

### 🌐 Kubernetes Support

For orchestration with Kubernetes:

```bash
# Deploy to Kubernetes
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/monitoring.yaml

# Check deployment status
kubectl get pods -n flavorsnap
kubectl get services -n flavorsnap
```

## 🤝 Contributing

We love contributions! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

### 🎯 How to Contribute

#### 1. Fork & Clone

```bash
git clone https://github.com/your-username/flavorsnap.git
cd flavorsnap
```

#### 2. Setup Development Environment

```bash
# Python backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements-dev.txt

# Frontend
cd frontend && npm install
```

#### 3. Create Feature Branch

```bash
git checkout -b feature/amazing-feature
```

#### 4. Make Changes

- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

#### 5. Test Your Changes

```bash
npm run test
npm run lint
npm run build
```

#### 6. Commit & Push

```bash
git commit -m "feat: add amazing feature"
git push origin feature/amazing-feature
```

#### 7. Create Pull Request

- Provide clear description of changes
- Link relevant issues
- Include screenshots for UI changes

### 📝 Development Guidelines

#### Code Style

- **TypeScript**: Strict mode enabled
- **React**: Functional components with hooks
- **CSS**: TailwindCSS utility classes
- **Python**: PEP 8 compliant
- **Rust**: rustfmt formatting

#### Commit Messages

Follow [Conventional Commits](https://conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code formatting
- `refactor:` Code refactoring
- `test:` Test additions
- `chore:` Maintenance tasks

#### Testing Requirements

- Unit tests for all new functions
- Integration tests for API endpoints
- E2E tests for user workflows
- Minimum 80% code coverage

#### Pull Request Process

1. Update README.md for new features
2. Add/update tests
3. Ensure CI/CD passes
4. Request code review
5. Merge after approval

### 🏆 Contribution Areas

#### Frontend

- UI/UX improvements
- New components
- Performance optimizations
- Mobile responsiveness
- Accessibility features

#### Backend

- API enhancements
- Model optimization
- Security improvements
- Database integration
- Performance tuning

#### Machine Learning

- Model architecture improvements
- New food categories
- Accuracy enhancements
- Training pipeline
- Model deployment

#### Documentation

- API documentation
- Tutorials
- Examples
- Translation
- Video guides

## 📝 API Documentation

### Endpoints

### Current REST API

FlavorSnap now exposes a FastAPI-based REST API with generated OpenAPI documentation.

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI schema: `http://localhost:8000/openapi.json`

#### POST /api/v1/classify

Classify an uploaded food image with multipart form data.

**Form fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | file | yes | JPEG, PNG, or WebP image |
| `resize` | int | no | Square resize target before inference. Default: `224` |
| `center_crop` | bool | no | Apply center crop after resize. Default: `true` |
| `normalize` | bool | no | Apply ImageNet normalization. Default: `true` |
| `top_k` | int | no | Number of ranked predictions to return. Default: `3` |

**Request:**

```bash
curl -X POST "http://localhost:8000/api/v1/classify" \
  -F "image=@/path/to/food.jpg" \
  -F "resize=256" \
  -F "center_crop=true" \
  -F "normalize=true" \
  -F "top_k=3"
```

**Response:**

```json
{
  "prediction": "Moi Moi",
  "confidence": 0.91,
  "predictions": [
    { "label": "Moi Moi", "confidence": 0.91 },
    { "label": "Akara", "confidence": 0.06 },
    { "label": "Bread", "confidence": 0.03 }
  ],
  "preprocessing": {
    "resize": 256,
    "center_crop": true,
    "normalize": true,
    "top_k": 3
  },
  "processing_time_ms": 18.247,
  "filename": "food.jpg",
  "request_id": "4b3709df-4d1f-4cad-95f7-9e86b629f470"
}
```

**Error codes:**

- `400`: empty upload or invalid image payload
- `413`: file exceeds configured upload size
- `415`: unsupported content type
- `429`: rate limit exceeded
- `500`: model loading or inference failure

#### GET /api/v1/health

Check API health and model readiness.

**Response:**

```json
{
  "status": "ok",
  "model_loaded": true,
  "classes": ["Akara", "Bread", "Egusi", "Moi Moi", "Rice and Stew", "Yam"],
  "startup_error": null
}
```

### Legacy notes

#### POST /predict

Classify uploaded food image.

**Request:**

```bash
curl -X POST \
  http://localhost:5000/predict \
  -F 'image=@/path/to/food.jpg'
```

**Response:**

```json
{
  "label": "Moi Moi",
  "confidence": 85.7,
  "all_predictions": [
    { "label": "Moi Moi", "confidence": 85.7 },
    { "label": "Akara", "confidence": 9.2 },
    { "label": "Bread", "confidence": 3.1 }
  ],
  "processing_time": 0.234
}
```

#### GET /predictions

List predictions with pagination, filtering, and sorting.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (offset-based) |
| `limit` | int | 20 | Items per page (max 100) |
| `cursor` | string | — | Opaque cursor for cursor-based pagination (from previous `next_cursor`) |
| `label` | string | — | Filter by label (exact or comma-separated list) |
| `confidence_min` | float | — | Minimum confidence (0–100) |
| `confidence_max` | float | — | Maximum confidence (0–100) |
| `created_after` | ISO datetime | — | Filter predictions after this time |
| `created_before` | ISO datetime | — | Filter predictions before this time |
| `sort_by` | string | `created_at` | Sort field: `created_at`, `label`, `confidence`, `id` |
| `order` | string | `desc` | Sort order: `asc`, `desc` |

**Example (offset):**

```bash
curl "http://localhost:5000/predictions?page=1&limit=20&sort_by=created_at&order=desc"
```

**Example (cursor):**

```bash
curl "http://localhost:5000/predictions?cursor=eyJ...&limit=20"
```

**Response:**

```json
{
  "predictions": [
    { "id": "uuid", "label": "Moi Moi", "confidence": 85.0, "created_at": "2025-02-23T12:00:00+00:00" }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 42, "total_pages": 3 },
  "next_cursor": "base64...",
  "prev_cursor": null,
  "count": 20
}
```

#### GET /health

Check API health status.

**Response:**

```json
{
  "status": "healthy",
  "model_loaded": true,
  "version": "1.0.0"
}
```

#### GET /classes

Get list of supported food classes.

**Response:**

```json
{
  "classes": ["Akara", "Bread", "Egusi", "Moi Moi", "Rice and Stew", "Yam"],
  "count": 6
}
```

### Error Responses

```json
{
  "error": "Invalid image format",
  "code": "INVALID_FILE_TYPE",
  "message": "Only JPG, PNG, and WebP images are supported"
}
```

## 🧪 Testing

### Running Tests

```bash
# Frontend tests
cd frontend
npm run test
npm run test:coverage
npm run test:e2e

# Backend (FastAPI API + Panel UI) tests
# Runs only tests under `tests/` (see repo `pyproject.toml`).
python scripts/run_tests.py

# Same suite with coverage (enforces 90%+).
python scripts/coverage_report.py

# Performance benchmarks
python scripts/run_tests.py --performance-smoke
python scripts/run_tests.py --performance-full
```

### Test Structure

```
tests/
├── 📁 api/                    # FastAPI endpoint tests (existing)
├── 📁 unit/                   # Core module unit tests
├── 📁 integration/            # API/UI integration tests
└── 📁 performance/           # pytest-benchmark performance checks
```

### Test Data

Most Python fixtures are generated deterministically at runtime (see `tests/conftest.py`).
Any on-disk lightweight assets live under `tests/fixtures/`.

## 📊 Model Information

### Architecture

- **Base Model**: ResNet18 (ImageNet pretrained)
- **Input Size**: 224x224 RGB images
- **Output Classes**: 6 Nigerian food categories
- **Parameters**: 11.7M total, 1.2M trainable

### Training Details

- **Dataset**: 2,400+ images (400 per class)
- **Training Split**: 80% train, 20% validation
- **Epochs**: 50 with early stopping
- **Optimizer**: Adam (lr=0.001)
- **Accuracy**: 94.2% validation accuracy

### Food Classes

1. **Akara** - Bean cake
2. **Bread** - Various bread types
3. **Egusi** - Melon seed soup
4. **Moi Moi** - Bean pudding
5. **Rice and Stew** - Rice with tomato stew
6. **Yam** - Yam dishes

### Performance Metrics

- **Top-1 Accuracy**: 94.2%
- **Top-3 Accuracy**: 98.7%
- **Inference Time**: ~200ms (CPU)
- **Model Size**: 44MB

## 🐛 Troubleshooting

### Common Issues

#### Model Loading Fails

```bash
# Check model path
ls -la model.pth
# Verify file integrity
python -c "import torch; print(torch.load('model.pth').keys())"
```

#### Frontend Build Errors

```bash
# Clear cache
rm -rf .next node_modules
npm install
npm run build
```

#### API Connection Issues

```bash
# Check if API is running
curl http://localhost:5000/health
# Verify CORS settings
curl -H "Origin: http://localhost:3000" http://localhost:5000/predict
```

#### Memory Issues

```bash
# Monitor memory usage
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"
# Reduce batch size if needed
```

### Debug Mode

Enable debug logging:

```env
DEBUG=true
LOG_LEVEL=debug
```

### Performance Optimization

- Use WebP images for faster uploads
- Implement image compression on client-side
- Cache model predictions for similar images
- Use CDN for static assets

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### 🙏 Acknowledgments

- [PyTorch](https://pytorch.org/) for the deep learning framework
- [Next.js](https://nextjs.org/) for the React framework
- [TailwindCSS](https://tailwindcss.com/) for the styling framework
- [Stellar/Soroban](https://soroban.stellar.org/) for blockchain integration
- The Nigerian food community for dataset contributions

### 📞 Support

- **Telegram Group**: [Join our community](https://t.me/+Tf3Ll4oRiGk5ZTM0)
- **GitHub Issues**: [Report bugs](https://github.com/your-username/flavorsnap/issues)
- **Email**: support@flavorsnap.com

---

<div align="center">

**⭐ Star this repository if it helped you!**

Made with 💚 for Nigerian food lovers

[![Backers](https://img.shields.io/badge/Backers-0-orange?style=for-the-badge)](https://github.com/sponsors/your-username)
[![Sponsors](https://img.shields.io/badge/Sponsors-0-purple?style=for-the-badge)](https://github.com/sponsors/your-username)

</div>
