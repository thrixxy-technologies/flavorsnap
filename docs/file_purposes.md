# 📄 FlavorSnap File Purposes and Responsibilities

## 📋 Table of Contents

- [🎯 Overview](#-overview)
- [📁 Root Files](#-root-files)
- [🏗️ Frontend Files](#️-frontend-files)
- [🧠 Machine Learning Files](#-machine-learning-files)
- [⛓️ Blockchain Files](#️-blockchain-files)
- [⚙️ Configuration Files](#️-configuration-files)
- [🐳 Container Files](#-container-files)
- [📚 Documentation Files](#-documentation-files)
- [🔧 Script Files](#-script-files)
- [🧪 Test Files](#-test-files)
- [📊 Data Files](#-data-files)

## 🎯 Overview

This document provides a comprehensive breakdown of every file and directory in the FlavorSnap project, explaining their purpose, responsibilities, and interconnections. Understanding these roles is crucial for effective development and maintenance.

### File Categories

1. **Core Application Files**: Main application logic
2. **Configuration Files**: Environment and deployment settings
3. **Documentation Files**: Project documentation and guides
4. **Build Files**: Compilation and packaging configurations
5. **Test Files**: Unit, integration, and E2E tests
6. **Data Files**: Models, datasets, and static assets

## 📁 Root Files

### Core Application Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `README.md` | Project documentation | Main project overview, setup instructions, features | All project components |
| `model.pth` | Trained ML model | Food classification model (44MB ResNet18) | PyTorch, ml-model-api |
| `food_classes.txt` | Food categories | List of supported food classes for classification | ML model, frontend |
| `config.yaml` | Main configuration | Central configuration for all components | All services |
| `train_model.ipynb` | Model training | Jupyter notebook for training/retraining models | PyTorch, dataset |
| `train_model.py` | Training script | Python script for automated model training | PyTorch, dataset |
| `dashboard.py` | Analytics dashboard | Panel-based dashboard for monitoring | Panel, analytics data |

### Build and Package Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `Cargo.toml` | Rust workspace | Rust project configuration and dependencies | Rust contracts |
| `package.json` | Node.js dependencies | Frontend dependencies and scripts (if exists) | Node.js ecosystem |
| `requirements.txt` | Python dependencies | Backend Python package list | Python ecosystem |

### Version Control Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `.gitignore` | Git ignore rules | Specifies files to exclude from version control | Git |
| `.dockerignore` | Docker ignore | Files to exclude from Docker builds | Docker |

## 🏗️ Frontend Files

### Next.js Application (`frontend/`)

#### Core Application Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `pages/index.tsx` | Landing page | Main application entry point, user interface | Next.js, React |
| `pages/classify.tsx` | Classification UI | Food classification interface | Next.js, ML API |
| `pages/api/` | API routes | Backend API endpoints for frontend | Next.js API |
| `app/` | App directory | Next.js 13+ app router structure | Next.js 13+ |

#### Component Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `components/ui/` | UI components | Reusable UI elements (buttons, forms) | React, Tailwind |
| `components/forms/` | Form components | Upload forms, classification forms | React Hook Form |
| `components/layout/` | Layout components | Header, footer, navigation | React |

#### Configuration Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `next.config.ts` | Next.js config | Framework configuration | Next.js |
| `tsconfig.json` | TypeScript config | Type checking configuration | TypeScript |
| `tailwind.config.ts` | Tailwind config | Styling framework setup | TailwindCSS |
| `next-i18next.config.js` | i18n config | Internationalization settings | next-i18next |

#### Development Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `package.json` | Dependencies | Frontend packages and scripts | npm/yarn |
| `package-lock.json` | Lock file | Exact dependency versions | npm |
| `.eslintrc.js` | ESLint config | Code linting rules | ESLint |
| `jest.config.js` | Jest config | Test framework configuration | Jest |
| `jest.setup.js` | Jest setup | Test environment setup | Jest |

#### Static Assets

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `public/images/` | Static images | Icons, hero images, logos | Frontend |
| `public/favicon.ico` | Favicon | Browser tab icon | Frontend |
| `styles/` | CSS files | Global styles, Tailwind imports | TailwindCSS |

## 🧠 Machine Learning Files

### Flask API (`ml-model-api/`)

#### Core Application Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `app.py` | Main Flask app | Web server entry point | Flask |
| `model_loader.py` | Model management | Loading and caching ML models | PyTorch |
| `api_endpoints.py` | API routes | RESTful endpoint definitions | Flask |
| `analytics.py` | Analytics | Classification analytics and metrics | Flask |
| `monitoring.py` | Performance monitoring | Health checks and metrics | Flask |

#### Advanced Features

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `xai.py` | Explainable AI | Model explanation features | PyTorch, SHAP |
| `batch_processor.py` | Batch processing | Handle multiple image classifications | PyTorch |
| `model_registry.py` | Model versioning | Model version management | PyTorch |
| `model_validator.py` | Model validation | Validate model performance | PyTorch |
| `deployment_manager.py` | Deployment | Model deployment orchestration | Docker |

#### API Extensions

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `category_management.py` | Category management | Food category CRUD operations | Flask |
| `category_routes.py` | Category routes | API endpoints for categories | Flask |
| `social_routes.py` | Social features | Social sharing endpoints | Flask |
| `social_sharing.py` | Social sharing | Social media integration | APIs |
| `batch_endpoints.py` | Batch endpoints | Batch processing API | Flask |
| `xai_routes.py` | XAI endpoints | Explainable AI API | Flask |

#### Configuration and Utilities

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `requirements.txt` | Dependencies | Python package list | pip |
| `logger_config.py` | Logging | Application logging configuration | Python logging |
| `swagger_setup.py` | API documentation | Swagger/OpenAPI setup | Flask |
| `openapi.yaml` | API spec | OpenAPI specification | OpenAPI |
| `performance_dashboard.py` | Dashboard | Performance monitoring dashboard | Panel |

#### Development Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `setup.sh` | Unix setup | Environment setup script | Bash |
| `setup.bat` | Windows setup | Environment setup script | Batch |
| `test_rate_limiter.py` | Rate limiting | API rate limiting tests | Flask |
| `ab_testing.py` | A/B testing | Model A/B testing framework | PyTorch |

## ⛓️ Blockchain Files

### Smart Contracts (`contracts/`)

#### Contract Directories

| Directory | Purpose | Responsibilities | Dependencies |
|-----------|---------|------------------|--------------|
| `model-governance/` | Model governance | Model version control, validation | Soroban |
| `tokenized-incentive/` | Token incentives | Reward system for contributions | Soroban |
| `sensory-evaluation/` | Sensory evaluation | Community feedback contracts | Soroban |

### Rust Registry (`flavorsnap-food-registry/`)

#### Core Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `Cargo.toml` | Rust project | Package configuration | Rust |
| `src/` | Source code | Rust implementation | Soroban SDK |
| `README.md` | Documentation | Component documentation | - |

## ⚙️ Configuration Files

### Application Configuration

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `config/default.yaml` | Default config | Base configuration for all environments | All services |
| `config/development.yaml` | Development config | Development-specific settings | Development |
| `config/production.yaml` | Production config | Production-specific settings | Production |
| `.env.example` | Environment template | Environment variable template | All services |

### Environment Configuration

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `.env` | Environment variables | Runtime configuration | All services |
| `.env.local` | Local env vars | Local development overrides | Local dev |
| `.env.production` | Production env | Production environment | Production |

## 🐳 Container Files

### Docker Configuration

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `Dockerfile` | Production image | Optimized production container | Production |
| `Dockerfile.dev` | Development image | Development container with tools | Development |
| `Dockerfile.frontend.dev` | Frontend dev | Frontend development container | Frontend |
| `.dockerignore` | Docker ignore | Files to exclude from builds | Docker |

### Docker Compose

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `docker-compose.yml` | Development stack | Local development environment | Development |
| `docker-compose.prod.yml` | Production stack | Production deployment | Production |
| `docker-compose.test.yml` | Testing stack | Testing environment | Testing |

## 📚 Documentation Files

### Core Documentation

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `docs/project_structure.md` | Structure docs | Project organization guide | - |
| `docs/blockchain.md` | Blockchain docs | Decentralized architecture and governance | Stellar/Soroban |
| `docs/development_workflow.md` | Workflow guide | Development process documentation | - |
| `docs/file_purposes.md` | File purposes | This file - file responsibilities | - |
| `docs/installation.md` | Installation guide | Setup and installation instructions | - |
| `docs/configuration.md` | Configuration guide | Configuration options and settings | - |
| `docs/troubleshooting.md` | Troubleshooting | Common issues and solutions | - |
| `contracts/README.md` | Contract docs | Technical guide for smart contracts | Soroban |

### Additional Documentation

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `SECURITY.md` | Security policy | Security guidelines and reporting | - |
| `CONTRIBUTING.md` | Contributing guide | Contribution guidelines | - |
| `LICENSE` | License | Project license information | - |
| `CHANGELOG.md` | Changelog | Version history and changes | - |

## 🔧 Script Files

### Setup and Installation

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `scripts/install.py` | Automated setup | Complete project installation | Python |
| `scripts/check_environment.py` | Environment check | Validate development environment | Python |
| `scripts/validate_config.py` | Config validation | Validate configuration files | Python |
| `scripts/docker_run.sh` | Docker runner | Docker container management | Bash |

### Development Scripts

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `scripts/analyze_structure.py` | Structure analysis | Project structure analysis | Python |
| `scripts/generate_test_data.py` | Test data generation | Create test datasets | Python |
| `scripts/deploy.sh` | Deployment script | Automated deployment | Bash |
| `scripts/release.sh` | Release script | Automated release process | Bash |

## 🧪 Test Files

### Frontend Tests

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `frontend/__tests__/` | Test files | Frontend unit and integration tests | Jest, React Testing Library |
| `frontend/jest.setup.js` | Test setup | Jest configuration | Jest |
| `frontend/jest.setup.ts` | TypeScript setup | TypeScript test configuration | Jest, TypeScript |

### Backend Tests

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `ml-model-api/tests/` | Test files | Backend unit and integration tests | pytest |
| `tests/fixtures/` | Test fixtures | Test data and mock objects | pytest |

### E2E Tests

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `tests/e2e/` | E2E tests | End-to-end application tests | Playwright/Cypress |

## 📊 Data Files

### Model Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `model.pth` | Trained model | Main classification model | PyTorch |
| `models/checkpoints/` | Checkpoints | Training checkpoints | PyTorch |
| `models/model_metadata.json` | Metadata | Model information and version | JSON |

### Dataset Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `dataset/train/` | Training data | Training images by class | ML pipeline |
| `dataset/test/` | Test data | Test images for validation | ML pipeline |
| `dataset/validation/` | Validation data | Validation dataset | ML pipeline |
| `dataset/data_split.py` | Data utilities | Dataset splitting and processing | Python |

### Upload Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `uploads/classified/` | Classified images | Organized by prediction | ML API |
| `uploads/temp/` | Temporary uploads | Temporary file storage | ML API |

### Static Files

| File | Purpose | Responsibilities | Dependencies |
|------|---------|------------------|--------------|
| `food.jpg` | Sample image | Sample food image for testing | Frontend |
| `test-food.jpg` | Test image | Test image for development | Testing |

## 🔗 File Interconnections

### Data Flow Dependencies

```
User Upload → Frontend → ML API → Model.pth → Database
     ↓              ↓         ↓         ↓        ↓
  UI Display    API Call  Inference  Model   Storage
```

### Configuration Dependencies

```
config.yaml → All Services
.env.example → Environment Setup
docker-compose.yml → Container Orchestration
```

### Build Dependencies

```
package.json → Frontend Build
requirements.txt → Backend Setup
Cargo.toml → Contract Compilation
```

## 📝 File Maintenance Guidelines

### Regular Updates

- **Dependencies**: Update monthly
- **Documentation**: Update with features
- **Configuration**: Review quarterly
- **Tests**: Update with code changes

### Backup Strategy

- **Model Files**: Version control with Git LFS
- **Configuration**: Environment-specific backups
- **Documentation**: Automated generation
- **Test Data**: Synthetic generation

### Security Considerations

- **Environment Files**: Never commit to version control
- **Secret Keys**: Use secret management
- **Model Files**: Validate integrity
- **Upload Files**: Scan for malware

---

## 📚 Additional Resources

- [Project Structure](project_structure.md)
- [Development Workflow](development_workflow.md)
- [Installation Guide](installation.md)
- [Configuration Guide](configuration.md)

---

*Last updated: March 2026*
*Version: 1.0.0*
