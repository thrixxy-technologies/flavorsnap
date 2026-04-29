#!/usr/bin/env python3
"""
Feature Documentation System for FlavorSnap ML Model API
Comprehensive feature documentation, cataloging, and knowledge management
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import sqlite3
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import uuid
from pathlib import Path
import threading
import markdown
from jinja2 import Template, Environment, FileSystemLoader
import matplotlib.pyplot as plt
import seaborn as sns

# Import our modules
from feature_extraction import ExtractedFeatures, FeatureType
from feature_selection import SelectionResult, SelectionMethod
from feature_importance import ImportanceResult, ImportanceMethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentationType(Enum):
    """Documentation types"""
    FEATURE_CATALOG = "feature_catalog"
    TECHNICAL_SPECIFICATION = "technical_specification"
    USER_GUIDE = "user_guide"
    API_DOCUMENTATION = "api_documentation"
    PERFORMANCE_REPORT = "performance_report"
    CHANGELOG = "changelog"

class DocumentationFormat(Enum):
    """Documentation output formats"""
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"
    JSON = "json"

@dataclass
class DocumentationConfig:
    """Feature documentation configuration"""
    # Documentation settings
    enable_auto_generation: bool = True
    update_frequency: str = "daily"  # "hourly", "daily", "weekly"
    include_visualizations: bool = True
    include_performance_metrics: bool = True
    include_usage_examples: bool = True
    
    # Output settings
    output_formats: List[DocumentationFormat] = None
    output_directory: str = "feature_documentation"
    template_directory: str = "documentation_templates"
    
    # Content settings
    include_feature_importance: bool = True
    include_selection_history: bool = True
    include_monitoring_data: bool = True
    include_version_history: bool = True
    
    # Search and indexing
    enable_search: bool = True
    enable_tagging: bool = True
    enable_categorization: bool = True
    
    # Collaboration settings
    enable_comments: bool = True
    enable_ratings: bool = True
    enable_feedback: bool = True
    
    # Database
    database_path: str = "feature_documentation.db"
    
    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = [DocumentationFormat.HTML, DocumentationFormat.MARKDOWN]

@dataclass
class FeatureDocumentation:
    """Individual feature documentation"""
    feature_id: str
    feature_name: str
    feature_type: FeatureType
    description: str
    extraction_method: str
    extraction_parameters: Dict[str, Any]
    data_type: str
    value_range: Optional[Tuple[float, float]]
    typical_values: List[float]
    importance_score: Optional[float]
    selection_methods: List[str]
    performance_metrics: Dict[str, float]
    usage_examples: List[str]
    tags: List[str]
    category: str
    created_at: datetime
    updated_at: datetime
    version: str
    metadata: Dict[str, Any]

@dataclass
class DocumentationPage:
    """Documentation page"""
    page_id: str
    title: str
    content: str
    page_type: DocumentationType
    format: DocumentationFormat
    author: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    metadata: Dict[str, Any]

@dataclass
class DocumentationComment:
    """Documentation comment"""
    comment_id: str
    feature_id: Optional[str]
    page_id: Optional[str]
    author: str
    content: str
    rating: Optional[int]
    created_at: datetime
    metadata: Dict[str, Any]

class FeatureDocumentationSystem:
    """Advanced feature documentation system"""
    
    def __init__(self, config: DocumentationConfig = None):
        self.config = config or DocumentationConfig()
        self.logger = logging.getLogger(__name__)
        
        # Documentation storage
        self.feature_docs = {}
        self.documentation_pages = {}
        self.comments = {}
        
        # Template engine
        self.template_env = self._setup_template_engine()
        
        # Database
        self.db_path = self.config.database_path
        self._init_database()
        
        # Directories
        self.output_dir = Path(self.config.output_directory)
        self.output_dir.mkdir(exist_ok=True)
        self.template_dir = Path(self.config.template_directory)
        self.template_dir.mkdir(exist_ok=True)
        
        # Thread safety
        self.doc_lock = threading.Lock()
        
        # Create default templates
        self._create_default_templates()
        
        logger.info("FeatureDocumentationSystem initialized")
    
    def _setup_template_engine(self):
        """Setup Jinja2 template engine"""
        try:
            env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=True
            )
            
            # Add custom filters
            env.filters['datetime'] = self._format_datetime
            env.filters['percentage'] = self._format_percentage
            env.filters['round'] = self._format_round
            
            return env
            
        except Exception as e:
            logger.error(f"Failed to setup template engine: {str(e)}")
            return Environment()
    
    def _format_datetime(self, value, format='%Y-%m-%d %H:%M:%S'):
        """Format datetime for templates"""
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        return value.strftime(format)
    
    def _format_percentage(self, value):
        """Format as percentage"""
        return f"{value * 100:.2f}%"
    
    def _format_round(self, value, decimals=2):
        """Round number"""
        return round(value, decimals)
    
    def _init_database(self):
        """Initialize documentation database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Feature documentation table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feature_documentation (
                    feature_id TEXT PRIMARY KEY,
                    feature_name TEXT NOT NULL,
                    feature_type TEXT NOT NULL,
                    description TEXT,
                    extraction_method TEXT,
                    extraction_parameters TEXT,
                    data_type TEXT,
                    value_range_min REAL,
                    value_range_max REAL,
                    typical_values TEXT,
                    importance_score REAL,
                    selection_methods TEXT,
                    performance_metrics TEXT,
                    usage_examples TEXT,
                    tags TEXT,
                    category TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version TEXT,
                    metadata TEXT
                )
            ''')
            
            # Documentation pages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documentation_pages (
                    page_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    page_type TEXT NOT NULL,
                    format TEXT NOT NULL,
                    author TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    tags TEXT,
                    metadata TEXT
                )
            ''')
            
            # Comments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documentation_comments (
                    comment_id TEXT PRIMARY KEY,
                    feature_id TEXT,
                    page_id TEXT,
                    author TEXT NOT NULL,
                    content TEXT NOT NULL,
                    rating INTEGER,
                    created_at TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (feature_id) REFERENCES feature_documentation (feature_id),
                    FOREIGN KEY (page_id) REFERENCES documentation_pages (page_id)
                )
            ''')
            
            # Search index table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    indexed_at TEXT NOT NULL
                )
            ''')
            
            # Categories table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    category_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    parent_category_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (parent_category_id) REFERENCES categories (category_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Documentation database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def _create_default_templates(self):
        """Create default documentation templates"""
        try:
            # Feature catalog template
            feature_catalog_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Feature Catalog - FlavorSnap</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .feature-card { border: 1px solid #ddd; padding: 20px; margin: 10px 0; border-radius: 5px; }
        .importance-high { border-left: 5px solid #ff6b6b; }
        .importance-medium { border-left: 5px solid #feca57; }
        .importance-low { border-left: 5px solid #48dbfb; }
        .metric { display: inline-block; margin: 5px; padding: 5px 10px; background: #f8f9fa; border-radius: 3px; }
        .tag { display: inline-block; margin: 2px; padding: 2px 8px; background: #e9ecef; border-radius: 12px; font-size: 12px; }
    </style>
</head>
<body>
    <h1>Feature Catalog</h1>
    <p>Total Features: {{ features|length }}</p>
    
    {% for category, category_features in features_by_category.items() %}
    <h2>{{ category }}</h2>
    {% for feature in category_features %}
    <div class="feature-card importance-{{ feature.importance_level }}">
        <h3>{{ feature.feature_name }}</h3>
        <p><strong>Type:</strong> {{ feature.feature_type.value }}</p>
        <p><strong>Description:</strong> {{ feature.description }}</p>
        <p><strong>Extraction Method:</strong> {{ feature.extraction_method }}</p>
        
        {% if feature.importance_score %}
        <p><strong>Importance Score:</strong> <span class="metric">{{ feature.importance_score|round(3) }}</span></p>
        {% endif %}
        
        {% if feature.performance_metrics %}
        <p><strong>Performance:</strong>
        {% for metric, value in feature.performance_metrics.items() %}
            <span class="metric">{{ metric }}: {{ value|round(3) }}</span>
        {% endfor %}
        </p>
        {% endif %}
        
        {% if feature.tags %}
        <p><strong>Tags:</strong>
        {% for tag in feature.tags %}
            <span class="tag">{{ tag }}</span>
        {% endfor %}
        </p>
        {% endif %}
        
        {% if feature.usage_examples %}
        <p><strong>Usage Examples:</strong></p>
        <ul>
        {% for example in feature.usage_examples %}
            <li>{{ example }}</li>
        {% endfor %}
        </ul>
        {% endif %}
    </div>
    {% endfor %}
    {% endfor %}
</body>
</html>
            """
            
            # Technical specification template
            tech_spec_template = """
# Technical Specification - {{ title }}

## Overview
{{ overview }}

## Feature Types
{% for feature_type in feature_types %}
### {{ feature_type.name }}
{{ feature_type.description }}

**Features:** {{ feature_type.count }}
{% endfor %}

## Extraction Methods
{% for method in extraction_methods %}
### {{ method.name }}
- **Description:** {{ method.description }}
- **Parameters:** {{ method.parameters }}
- **Performance:** {{ method.performance_metrics }}
{% endfor %}

## Selection Algorithms
{% for algorithm in selection_algorithms %}
### {{ algorithm.name }}
- **Method:** {{ algorithm.method }}
- **Performance:** {{ algorithm.performance }}
- **Best For:** {{ algorithm.best_for }}
{% endfor %}

## Performance Metrics
{% for metric in performance_metrics %}
- **{{ metric.name }}:** {{ metric.value }}
{% endfor %}

## API Reference
{% for endpoint in api_endpoints %}
### {{ endpoint.path }}
- **Method:** {{ endpoint.method }}
- **Description:** {{ endpoint.description }}
- **Parameters:** {{ endpoint.parameters }}
{% endfor %}

*Generated on: {{ generation_date|datetime }}*
            """
            
            # Save templates
            with open(self.template_dir / "feature_catalog.html", 'w') as f:
                f.write(feature_catalog_template)
            
            with open(self.template_dir / "technical_specification.md", 'w') as f:
                f.write(tech_spec_template)
            
            logger.info("Default templates created")
            
        except Exception as e:
            logger.error(f"Failed to create default templates: {str(e)}")
    
    def document_feature(self, feature_name: str, feature_type: FeatureType,
                         description: str, extraction_method: str,
                         extraction_parameters: Dict[str, Any] = None,
                         importance_score: Optional[float] = None,
                         performance_metrics: Dict[str, float] = None,
                         usage_examples: List[str] = None,
                         tags: List[str] = None, category: str = "General") -> FeatureDocumentation:
        """Document a single feature"""
        try:
            with self.doc_lock:
                feature_id = str(uuid.uuid4())
                created_at = datetime.now()
                
                doc = FeatureDocumentation(
                    feature_id=feature_id,
                    feature_name=feature_name,
                    feature_type=feature_type,
                    description=description,
                    extraction_method=extraction_method,
                    extraction_parameters=extraction_parameters or {},
                    data_type="unknown",  # Would be determined from actual data
                    value_range=None,
                    typical_values=[],
                    importance_score=importance_score,
                    selection_methods=[],
                    performance_metrics=performance_metrics or {},
                    usage_examples=usage_examples or [],
                    tags=tags or [],
                    category=category,
                    created_at=created_at,
                    updated_at=created_at,
                    version="1.0.0",
                    metadata={}
                )
                
                # Save documentation
                self.feature_docs[feature_id] = doc
                self._save_feature_documentation(doc)
                
                # Update search index
                self._update_search_index(feature_id, "feature", self._create_search_content(doc))
                
                logger.info(f"Documented feature: {feature_name}")
                return doc
                
        except Exception as e:
            logger.error(f"Failed to document feature: {str(e)}")
            raise
    
    def document_features_from_extraction(self, extracted_features: Dict[str, ExtractedFeatures]):
        """Document features from extraction results"""
        try:
            documented_count = 0
            
            for image_path, features_dict in extracted_features.items():
                for feature_type, extracted_feature in features_dict.items():
                    for feature_name, feature_value in extracted_feature.features.items():
                        # Determine data type and value range
                        data_type, value_range, typical_values = self._analyze_feature_value(feature_value)
                        
                        # Create documentation
                        doc = self.document_feature(
                            feature_name=feature_name,
                            feature_type=feature_type,
                            description=f"Feature extracted using {feature_type.value} method",
                            extraction_method=feature_type.value,
                            extraction_parameters=extracted_feature.metadata,
                            data_type=data_type,
                            importance_score=None,  # Would be calculated from importance analysis
                            usage_examples=[f"Used in {feature_type.value} analysis"],
                            tags=[feature_type.value, "extracted"],
                            category=feature_type.value
                        )
                        
                        # Update with analyzed data
                        doc.data_type = data_type
                        doc.value_range = value_range
                        doc.typical_values = typical_values
                        self._save_feature_documentation(doc)
                        
                        documented_count += 1
            
            logger.info(f"Documented {documented_count} features from extraction")
            
        except Exception as e:
            logger.error(f"Failed to document features from extraction: {str(e)}")
    
    def _analyze_feature_value(self, feature_value: Any) -> Tuple[str, Optional[Tuple[float, float]], List[float]]:
        """Analyze feature value to determine type and range"""
        try:
            if isinstance(feature_value, (int, float)):
                return "numerical", (float(feature_value), float(feature_value)), [float(feature_value)]
            elif isinstance(feature_value, list):
                if all(isinstance(v, (int, float)) for v in feature_value):
                    values = [float(v) for v in feature_value]
                    return "numerical_array", (min(values), max(values)), values
                else:
                    return "mixed_array", None, []
            elif isinstance(feature_value, dict):
                return "dictionary", None, []
            elif isinstance(feature_value, str):
                return "text", None, []
            else:
                return "unknown", None, []
                
        except Exception as e:
            logger.error(f"Failed to analyze feature value: {str(e)}")
            return "unknown", None, []
    
    def document_selection_results(self, selection_results: Dict[SelectionMethod, SelectionResult]):
        """Document feature selection results"""
        try:
            for method, result in selection_results.items():
                for feature_name in result.selected_features:
                    # Update existing feature documentation
                    for doc in self.feature_docs.values():
                        if doc.feature_name == feature_name:
                            if method.value not in doc.selection_methods:
                                doc.selection_methods.append(method.value)
                            
                            # Update performance metrics
                            if result.performance_score:
                                doc.performance_metrics[f"selection_{method.value}_score"] = result.performance_score
                            
                            doc.updated_at = datetime.now()
                            self._save_feature_documentation(doc)
                            break
            
            logger.info(f"Documented selection results for {len(selection_results)} methods")
            
        except Exception as e:
            logger.error(f"Failed to document selection results: {str(e)}")
    
    def document_importance_results(self, importance_results: Dict[ImportanceMethod, ImportanceResult]):
        """Document feature importance results"""
        try:
            for method, result in importance_results.items():
                for i, feature_name in enumerate(result.feature_names):
                    importance_score = result.importance_scores[i]
                    
                    # Update existing feature documentation
                    for doc in self.feature_docs.values():
                        if doc.feature_name == feature_name:
                            doc.importance_score = importance_score
                            doc.performance_metrics[f"importance_{method.value}"] = importance_score
                            doc.updated_at = datetime.now()
                            self._save_feature_documentation(doc)
                            break
            
            logger.info(f"Documented importance results for {len(importance_results)} methods")
            
        except Exception as e:
            logger.error(f"Failed to document importance results: {str(e)}")
    
    def generate_feature_catalog(self, format: DocumentationFormat = DocumentationFormat.HTML) -> str:
        """Generate feature catalog documentation"""
        try:
            # Prepare data
            features = list(self.feature_docs.values())
            
            # Group by category
            features_by_category = {}
            for feature in features:
                if feature.category not in features_by_category:
                    features_by_category[feature.category] = []
                features_by_category[feature.category].append(feature)
            
            # Determine importance levels
            for feature in features:
                if feature.importance_score:
                    if feature.importance_score >= 0.8:
                        feature.importance_level = "high"
                    elif feature.importance_score >= 0.5:
                        feature.importance_level = "medium"
                    else:
                        feature.importance_level = "low"
                else:
                    feature.importance_level = "unknown"
            
            # Sort features by importance
            for category in features_by_category:
                features_by_category[category].sort(
                    key=lambda f: f.importance_score or 0, 
                    reverse=True
                )
            
            # Generate content
            if format == DocumentationFormat.HTML:
                template = self.template_env.get_template("feature_catalog.html")
                content = template.render(
                    features=features,
                    features_by_category=features_by_category
                )
            elif format == DocumentationFormat.MARKDOWN:
                content = self._generate_markdown_catalog(features, features_by_category)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Save documentation page
            page_id = str(uuid.uuid4())
            page = DocumentationPage(
                page_id=page_id,
                title="Feature Catalog",
                content=content,
                page_type=DocumentationType.FEATURE_CATALOG,
                format=format,
                author="system",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["catalog", "features"],
                metadata={"generation_date": datetime.now().isoformat()}
            )
            
            self.documentation_pages[page_id] = page
            self._save_documentation_page(page)
            
            # Save to file
            filename = f"feature_catalog.{format.value}"
            filepath = self.output_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Generated feature catalog in {format.value} format")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate feature catalog: {str(e)}")
            raise
    
    def _generate_markdown_catalog(self, features: List[FeatureDocumentation], 
                                 features_by_category: Dict[str, List[FeatureDocumentation]]) -> str:
        """Generate markdown feature catalog"""
        try:
            content = "# Feature Catalog\n\n"
            content += f"Total Features: {len(features)}\n\n"
            
            for category, category_features in features_by_category.items():
                content += f"## {category}\n\n"
                
                for feature in category_features:
                    content += f"### {feature.feature_name}\n\n"
                    content += f"**Type:** {feature.feature_type.value}\n\n"
                    content += f"**Description:** {feature.description}\n\n"
                    content += f"**Extraction Method:** {feature.extraction_method}\n\n"
                    
                    if feature.importance_score:
                        content += f"**Importance Score:** {feature.importance_score:.3f}\n\n"
                    
                    if feature.performance_metrics:
                        content += "**Performance Metrics:**\n"
                        for metric, value in feature.performance_metrics.items():
                            content += f"- {metric}: {value:.3f}\n"
                        content += "\n"
                    
                    if feature.tags:
                        content += f"**Tags:** {', '.join(feature.tags)}\n\n"
                    
                    if feature.usage_examples:
                        content += "**Usage Examples:**\n"
                        for example in feature.usage_examples:
                            content += f"- {example}\n"
                        content += "\n"
                    
                    content += "---\n\n"
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to generate markdown catalog: {str(e)}")
            return ""
    
    def generate_technical_specification(self) -> str:
        """Generate technical specification documentation"""
        try:
            # Collect data
            feature_types = {}
            for doc in self.feature_docs.values():
                ftype = doc.feature_type.value
                if ftype not in feature_types:
                    feature_types[ftype] = {
                        "name": ftype,
                        "description": f"Features of type {ftype}",
                        "count": 0
                    }
                feature_types[ftype]["count"] += 1
            
            extraction_methods = {}
            for doc in self.feature_docs.values():
                method = doc.extraction_method
                if method not in extraction_methods:
                    extraction_methods[method] = {
                        "name": method,
                        "description": f"Extraction using {method}",
                        "parameters": {},
                        "performance_metrics": {}
                    }
            
            selection_algorithms = []
            # Would be populated from selection results
            
            performance_metrics = {}
            for doc in self.feature_docs.values():
                for metric, value in doc.performance_metrics.items():
                    if metric not in performance_metrics:
                        performance_metrics[metric] = []
                    performance_metrics[metric].append(value)
            
            # Calculate averages
            for metric in performance_metrics:
                values = performance_metrics[metric]
                performance_metrics[metric] = {
                    "name": metric,
                    "value": np.mean(values),
                    "std": np.std(values)
                }
            
            # Generate content
            template = self.template_env.get_template("technical_specification.md")
            content = template.render(
                title="FlavorSnap Feature Engineering",
                overview="Advanced feature engineering pipeline for food image classification",
                feature_types=list(feature_types.values()),
                extraction_methods=list(extraction_methods.values()),
                selection_algorithms=selection_algorithms,
                performance_metrics=list(performance_metrics.values()),
                api_endpoints=[],  # Would be populated from API documentation
                generation_date=datetime.now()
            )
            
            # Save documentation page
            page_id = str(uuid.uuid4())
            page = DocumentationPage(
                page_id=page_id,
                title="Technical Specification",
                content=content,
                page_type=DocumentationType.TECHNICAL_SPECIFICATION,
                format=DocumentationFormat.MARKDOWN,
                author="system",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["technical", "specification"],
                metadata={"generation_date": datetime.now().isoformat()}
            )
            
            self.documentation_pages[page_id] = page
            self._save_documentation_page(page)
            
            # Save to file
            filepath = self.output_dir / "technical_specification.md"
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("Generated technical specification")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate technical specification: {str(e)}")
            raise
    
    def generate_user_guide(self) -> str:
        """Generate user guide documentation"""
        try:
            content = """# User Guide - FlavorSnap Feature Engineering

## Introduction
The FlavorSnap Feature Engineering system provides comprehensive tools for extracting, selecting, and managing features for food image classification.

## Getting Started

### Feature Extraction
```python
from feature_extraction import AutomatedFeatureExtractor

# Create extractor
extractor = AutomatedFeatureExtractor()

# Extract features from image
features = extractor.extract_all_features("path/to/image.jpg")
```

### Feature Selection
```python
from feature_selection import FeatureSelector

# Create selector
selector = FeatureSelector()

# Select features
results = selector.select_features(X, y, feature_names)
```

### Feature Engineering Pipeline
```python
from feature_engineering import FeatureEngineeringPipeline

# Create pipeline
pipeline = FeatureEngineeringPipeline()

# Run pipeline
result = pipeline.run_pipeline("path/to/data")
```

## Feature Types

### Color Features
- RGB color moments
- HSV color statistics
- Color histograms
- Dominant colors

### Texture Features
- GLCM (Gray-Level Co-occurrence Matrix)
- Local Binary Patterns (LBP)
- Gabor filters

### Shape Features
- Hu moments
- Contour-based features
- SIFT keypoints

### Deep Features
- CNN-based embeddings
- Pre-trained model features

## Best Practices

1. **Data Quality**: Ensure high-quality input images
2. **Feature Selection**: Use multiple selection methods
3. **Monitoring**: Track feature performance over time
4. **Versioning**: Keep track of feature versions
5. **Documentation**: Document custom features

## Troubleshooting

### Common Issues

**Memory Usage**: Large feature sets may require significant memory
- Solution: Use feature selection to reduce dimensionality

**Processing Time**: Complex features may be slow to extract
- Solution: Use caching and parallel processing

**Feature Drift**: Features may change over time
- Solution: Use monitoring system to detect drift

## API Reference

### AutomatedFeatureExtractor
- `extract_all_features(image_path)`: Extract all feature types
- `extract_color_features(image)`: Extract color features only
- `get_feature_summary(image_path)`: Get feature summary

### FeatureSelector
- `select_features(X, y, methods)`: Select features using specified methods
- `compare_methods(results)`: Compare selection methods
- `export_results(results, path)`: Export results

### FeatureEngineeringPipeline
- `run_pipeline(data_path)`: Run complete pipeline
- `get_pipeline_history()`: Get execution history
- `export_results(path)`: Export pipeline results

## Examples

### Basic Usage
```python
# Extract and select features
extractor = AutomatedFeatureExtractor()
selector = FeatureSelector()

# Extract features
features = extractor.extract_all_features("food.jpg")

# Select best features
X, y = prepare_data(features)
results = selector.select_features(X, y)

# Get best selection
best = selector.get_best_features()
print(f"Selected {len(best.selected_features)} features")
```

### Advanced Usage
```python
# Custom configuration
from feature_extraction import FeatureConfig
from feature_selection import SelectionConfig

# Configure extraction
extract_config = FeatureConfig(
    enable_deep_features=True,
    color_spaces=["rgb", "hsv", "lab"]
)

# Configure selection
select_config = SelectionConfig(
    task_type="classification",
    methods=[SelectionMethod.RANDOM_FOREST_IMPORTANCE]
)

# Create pipeline
pipeline = FeatureEngineeringPipeline(
    extraction_config=extract_config,
    selection_config=select_config
)
```

## Support

For support and questions:
- Check the documentation
- Review the examples
- Contact the development team

*Last updated: {generation_date}*
            """.format(generation_date=datetime.now().strftime("%Y-%m-%d"))
            
            # Save documentation page
            page_id = str(uuid.uuid4())
            page = DocumentationPage(
                page_id=page_id,
                title="User Guide",
                content=content,
                page_type=DocumentationType.USER_GUIDE,
                format=DocumentationFormat.MARKDOWN,
                author="system",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["guide", "user", "tutorial"],
                metadata={"generation_date": datetime.now().isoformat()}
            )
            
            self.documentation_pages[page_id] = page
            self._save_documentation_page(page)
            
            # Save to file
            filepath = self.output_dir / "user_guide.md"
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("Generated user guide")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate user guide: {str(e)}")
            raise
    
    def add_comment(self, feature_id: str = None, page_id: str = None,
                   author: str = "anonymous", content: str = "",
                   rating: Optional[int] = None) -> DocumentationComment:
        """Add comment to feature or page"""
        try:
            comment_id = str(uuid.uuid4())
            created_at = datetime.now()
            
            comment = DocumentationComment(
                comment_id=comment_id,
                feature_id=feature_id,
                page_id=page_id,
                author=author,
                content=content,
                rating=rating,
                created_at=created_at,
                metadata={}
            )
            
            self.comments[comment_id] = comment
            self._save_comment(comment)
            
            logger.info(f"Added comment from {author}")
            return comment
            
        except Exception as e:
            logger.error(f"Failed to add comment: {str(e)}")
            raise
    
    def search_documentation(self, query: str, item_type: str = "all") -> List[Dict[str, Any]]:
        """Search documentation"""
        try:
            if not self.config.enable_search:
                return []
            
            query_lower = query.lower()
            results = []
            
            # Search feature documentation
            if item_type in ["all", "feature"]:
                for doc in self.feature_docs.values():
                    search_content = f"{doc.feature_name} {doc.description} {' '.join(doc.tags)}".lower()
                    if query_lower in search_content:
                        results.append({
                            "type": "feature",
                            "id": doc.feature_id,
                            "title": doc.feature_name,
                            "description": doc.description,
                            "relevance": self._calculate_relevance(query_lower, search_content)
                        })
            
            # Search documentation pages
            if item_type in ["all", "page"]:
                for page in self.documentation_pages.values():
                    search_content = f"{page.title} {page.content} {' '.join(page.tags)}".lower()
                    if query_lower in search_content:
                        results.append({
                            "type": "page",
                            "id": page.page_id,
                            "title": page.title,
                            "description": page.content[:200] + "...",
                            "relevance": self._calculate_relevance(query_lower, search_content)
                        })
            
            # Sort by relevance
            results.sort(key=lambda x: x["relevance"], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search documentation: {str(e)}")
            return []
    
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate search relevance score"""
        try:
            # Simple relevance calculation based on term frequency
            query_terms = query.split()
            content_terms = content.split()
            
            matches = sum(1 for term in query_terms if term in content)
            total_terms = len(query_terms)
            
            if total_terms == 0:
                return 0.0
            
            return matches / total_terms
            
        except Exception as e:
            logger.error(f"Failed to calculate relevance: {str(e)}")
            return 0.0
    
    def _create_search_content(self, doc: FeatureDocumentation) -> str:
        """Create search content for feature documentation"""
        try:
            content_parts = [
                doc.feature_name,
                doc.description,
                doc.extraction_method,
                ' '.join(doc.tags),
                ' '.join(doc.usage_examples),
                doc.category
            ]
            
            return ' '.join(filter(None, content_parts))
            
        except Exception as e:
            logger.error(f"Failed to create search content: {str(e)}")
            return ""
    
    def _update_search_index(self, item_id: str, item_type: str, content: str):
        """Update search index"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO search_index 
                (item_id, item_type, content, indexed_at)
                VALUES (?, ?, ?, ?)
            ''', (item_id, item_type, content, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update search index: {str(e)}")
    
    def _save_feature_documentation(self, doc: FeatureDocumentation):
        """Save feature documentation to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO feature_documentation 
                (feature_id, feature_name, feature_type, description, extraction_method,
                 extraction_parameters, data_type, value_range_min, value_range_max,
                 typical_values, importance_score, selection_methods, performance_metrics,
                 usage_examples, tags, category, created_at, updated_at, version, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc.feature_id,
                doc.feature_name,
                doc.feature_type.value,
                doc.description,
                doc.extraction_method,
                json.dumps(doc.extraction_parameters),
                doc.data_type,
                doc.value_range[0] if doc.value_range else None,
                doc.value_range[1] if doc.value_range else None,
                json.dumps(doc.typical_values),
                doc.importance_score,
                json.dumps(doc.selection_methods),
                json.dumps(doc.performance_metrics),
                json.dumps(doc.usage_examples),
                json.dumps(doc.tags),
                doc.category,
                doc.created_at.isoformat(),
                doc.updated_at.isoformat(),
                doc.version,
                json.dumps(doc.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save feature documentation: {str(e)}")
    
    def _save_documentation_page(self, page: DocumentationPage):
        """Save documentation page to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO documentation_pages 
                (page_id, title, content, page_type, format, author,
                 created_at, updated_at, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                page.page_id,
                page.title,
                page.content,
                page.page_type.value,
                page.format.value,
                page.author,
                page.created_at.isoformat(),
                page.updated_at.isoformat(),
                json.dumps(page.tags),
                json.dumps(page.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save documentation page: {str(e)}")
    
    def _save_comment(self, comment: DocumentationComment):
        """Save comment to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO documentation_comments 
                (comment_id, feature_id, page_id, author, content, rating, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                comment.comment_id,
                comment.feature_id,
                comment.page_id,
                comment.author,
                comment.content,
                comment.rating,
                comment.created_at.isoformat(),
                json.dumps(comment.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save comment: {str(e)}")
    
    def get_documentation_summary(self) -> Dict[str, Any]:
        """Get documentation system summary"""
        try:
            summary = {
                "total_features": len(self.feature_docs),
                "total_pages": len(self.documentation_pages),
                "total_comments": len(self.comments),
                "feature_types": list(set(doc.feature_type.value for doc in self.feature_docs.values())),
                "categories": list(set(doc.category for doc in self.feature_docs.values())),
                "config": asdict(self.config)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get documentation summary: {str(e)}")
            return {}
    
    def export_documentation(self, output_path: str, format: str = "json"):
        """Export documentation data"""
        try:
            export_data = {
                "summary": self.get_documentation_summary(),
                "features": {},
                "pages": {},
                "comments": {}
            }
            
            # Export feature documentation
            for feature_id, doc in self.feature_docs.items():
                doc_data = asdict(doc)
                doc_data["feature_type"] = doc.feature_type.value
                doc_data["created_at"] = doc.created_at.isoformat()
                doc_data["updated_at"] = doc.updated_at.isoformat()
                export_data["features"][feature_id] = doc_data
            
            # Export documentation pages
            for page_id, page in self.documentation_pages.items():
                page_data = asdict(page)
                page_data["page_type"] = page.page_type.value
                page_data["format"] = page.format.value
                page_data["created_at"] = page.created_at.isoformat()
                page_data["updated_at"] = page.updated_at.isoformat()
                export_data["pages"][page_id] = page_data
            
            # Export comments
            for comment_id, comment in self.comments.items():
                comment_data = asdict(comment)
                comment_data["created_at"] = comment.created_at.isoformat()
                export_data["comments"][comment_id] = comment_data
            
            if format.lower() == "json":
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Documentation exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export documentation: {str(e)}")
            raise

# Utility functions
def create_default_documenter() -> FeatureDocumentationSystem:
    """Create documentation system with default configuration"""
    config = DocumentationConfig()
    return FeatureDocumentationSystem(config)

def create_custom_documenter(**kwargs) -> FeatureDocumentationSystem:
    """Create documentation system with custom configuration"""
    config = DocumentationConfig(**kwargs)
    return FeatureDocumentationSystem(config)

if __name__ == "__main__":
    # Example usage
    documenter = create_default_documenter()
    
    try:
        # Document a sample feature
        doc = documenter.document_feature(
            feature_name="color_histogram_red",
            feature_type=FeatureType.COLOR,
            description="Red color histogram feature for food classification",
            extraction_method="histogram",
            extraction_parameters={"bins": 256, "range": [0, 255]},
            importance_score=0.85,
            tags=["color", "histogram", "red"],
            category="Color Features"
        )
        
        print(f"Documented feature: {doc.feature_name}")
        
        # Generate documentation
        catalog_path = documenter.generate_feature_catalog()
        spec_path = documenter.generate_technical_specification()
        guide_path = documenter.generate_user_guide()
        
        print(f"Generated documentation:")
        print(f"- Catalog: {catalog_path}")
        print(f"- Spec: {spec_path}")
        print(f"- Guide: {guide_path}")
        
        # Get summary
        summary = documenter.get_documentation_summary()
        print(f"Documentation summary: {summary}")
        
        # Export documentation
        documenter.export_documentation("documentation_export.json")
        
    except Exception as e:
        print(f"Error: {str(e)}")
