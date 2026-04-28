"""
JSON Exporter - Export classification results to JSON format
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import base64
from PIL import Image
import io


class JSONExporter:
    """Handles JSON export operations"""
    
    def __init__(self):
        self.export_dir = "exports"
        os.makedirs(self.export_dir, exist_ok=True)
    
    def export_single(self, result_data: Dict[str, Any], filename: str) -> str:
        """
        Export a single classification result to JSON
        
        Args:
            result_data: Dictionary containing classification result
            filename: Filename without extension
            
        Returns:
            Path to exported JSON file
        """
        filepath = os.path.join(self.export_dir, f"{filename}.json")
        
        # Prepare data for JSON
        json_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'format_version': '1.0',
                'export_type': 'single_classification'
            },
            'classification': {
                'timestamp': result_data.get('timestamp', ''),
                'predicted_class': result_data.get('predicted_class', ''),
                'confidence': result_data.get('confidence', 0.0),
                'image_included': result_data.get('image_data') is not None
            }
        }
        
        # Add image data if present
        if result_data.get('image_data'):
            json_data['classification']['image_data'] = self._image_to_base64(result_data['image_data'])
        
        # Write to JSON file
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)
        
        return filepath
    
    def export_batch(self, results: List[Dict[str, Any]], filename: str) -> str:
        """
        Export multiple classification results to JSON
        
        Args:
            results: List of classification result dictionaries
            filename: Filename without extension
            
        Returns:
            Path to exported JSON file
        """
        filepath = os.path.join(self.export_dir, f"{filename}.json")
        
        # Prepare batch data
        json_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'format_version': '1.0',
                'export_type': 'batch_classification',
                'total_results': len(results)
            },
            'classifications': []
        }
        
        # Add each result
        for i, result in enumerate(results):
            classification_data = {
                'index': i,
                'timestamp': result.get('timestamp', ''),
                'predicted_class': result.get('predicted_class', ''),
                'confidence': result.get('confidence', 0.0),
                'image_included': result.get('image_data') is not None
            }
            
            # Add image data if present
            if result.get('image_data'):
                classification_data['image_data'] = self._image_to_base64(result['image_data'])
            
            json_data['classifications'].append(classification_data)
        
        # Write to JSON file
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)
        
        return filepath
    
    def export_with_metadata(self, 
                           results: List[Dict[str, Any]], 
                           metadata: Dict[str, Any],
                           filename: str) -> str:
        """
        Export results with additional metadata to JSON
        
        Args:
            results: List of classification result dictionaries
            metadata: Additional metadata to include
            filename: Filename without extension
            
        Returns:
            Path to exported JSON file
        """
        filepath = os.path.join(self.export_dir, f"{filename}.json")
        
        # Prepare data with metadata
        json_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'format_version': '1.0',
                'export_type': 'batch_with_metadata',
                'total_results': len(results)
            },
            'metadata': metadata,
            'classifications': []
        }
        
        # Add each result
        for i, result in enumerate(results):
            classification_data = {
                'index': i,
                'timestamp': result.get('timestamp', ''),
                'predicted_class': result.get('predicted_class', ''),
                'confidence': result.get('confidence', 0.0),
                'image_included': result.get('image_data') is not None
            }
            
            # Add image data if present
            if result.get('image_data'):
                classification_data['image_data'] = self._image_to_base64(result['image_data'])
            
            json_data['classifications'].append(classification_data)
        
        # Write to JSON file
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)
        
        return filepath
    
    def create_analysis_report(self, results: List[Dict[str, Any]], filename: str) -> str:
        """
        Create a detailed analysis JSON with statistics and insights
        
        Args:
            results: List of classification result dictionaries
            filename: Filename without extension
            
        Returns:
            Path to exported analysis JSON file
        """
        filepath = os.path.join(self.export_dir, f"{filename}_analysis.json")
        
        if not results:
            analysis_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'format_version': '1.0',
                    'export_type': 'analysis_report'
                },
                'summary': {
                    'total_classifications': 0,
                    'unique_classes': 0,
                    'avg_confidence': 0.0
                },
                'class_distribution': {},
                'confidence_distribution': {},
                'insights': ['No data available for analysis']
            }
        else:
            # Calculate statistics
            classes = [r.get('predicted_class', '') for r in results]
            confidences = [r.get('confidence', 0) for r in results]
            
            class_counts = {}
            for cls in classes:
                class_counts[cls] = class_counts.get(cls, 0) + 1
            
            # Confidence ranges
            confidence_ranges = {
                'high (>0.8)': sum(1 for c in confidences if c > 0.8),
                'medium (0.5-0.8)': sum(1 for c in confidences if 0.5 <= c <= 0.8),
                'low (<0.5)': sum(1 for c in confidences if c < 0.5)
            }
            
            # Generate insights
            insights = []
            insights.append(f"Total classifications: {len(results)}")
            insights.append(f"Unique food classes identified: {len(class_counts)}")
            insights.append(f"Average confidence: {sum(confidences) / len(confidences):.2%}")
            
            most_common_class = max(class_counts.items(), key=lambda x: x[1]) if class_counts else None
            if most_common_class:
                insights.append(f"Most common classification: {most_common_class[0]} ({most_common_class[1]} times)")
            
            analysis_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'format_version': '1.0',
                    'export_type': 'analysis_report'
                },
                'summary': {
                    'total_classifications': len(results),
                    'unique_classes': len(class_counts),
                    'avg_confidence': sum(confidences) / len(confidences),
                    'min_confidence': min(confidences),
                    'max_confidence': max(confidences)
                },
                'class_distribution': class_counts,
                'confidence_distribution': confidence_ranges,
                'insights': insights
            }
        
        # Write analysis to JSON
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(analysis_data, jsonfile, indent=2, ensure_ascii=False)
        
        return filepath
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 string
        
        Args:
            image: PIL Image object
            
        Returns:
            Base64 encoded image string
        """
        # Convert image to bytes
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        
        # Encode to base64
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        
        return base64_string
