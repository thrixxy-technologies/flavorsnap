"""
CSV Exporter - Export classification results to CSV format
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd


class CSVExporter:
    """Handles CSV export operations"""
    
    def __init__(self):
        self.export_dir = "exports"
        os.makedirs(self.export_dir, exist_ok=True)
    
    def export_single(self, result_data: Dict[str, Any], filename: str) -> str:
        """
        Export a single classification result to CSV
        
        Args:
            result_data: Dictionary containing classification result
            filename: Filename without extension
            
        Returns:
            Path to exported CSV file
        """
        filepath = os.path.join(self.export_dir, f"{filename}.csv")
        
        # Prepare data for CSV
        csv_data = {
            'timestamp': result_data.get('timestamp', ''),
            'predicted_class': result_data.get('predicted_class', ''),
            'confidence': result_data.get('confidence', 0.0),
            'image_included': result_data.get('image_data') is not None
        }
        
        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'predicted_class', 'confidence', 'image_included']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerow(csv_data)
        
        return filepath
    
    def export_batch(self, results: List[Dict[str, Any]], filename: str) -> str:
        """
        Export multiple classification results to CSV
        
        Args:
            results: List of classification result dictionaries
            filename: Filename without extension
            
        Returns:
            Path to exported CSV file
        """
        filepath = os.path.join(self.export_dir, f"{filename}.csv")
        
        # Prepare data for CSV
        csv_rows = []
        for result in results:
            csv_rows.append({
                'timestamp': result.get('timestamp', ''),
                'predicted_class': result.get('predicted_class', ''),
                'confidence': result.get('confidence', 0.0),
                'image_included': result.get('image_data') is not None
            })
        
        # Write to CSV using pandas for better formatting
        df = pd.DataFrame(csv_rows)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        return filepath
    
    def export_with_metadata(self, 
                           results: List[Dict[str, Any]], 
                           metadata: Dict[str, Any],
                           filename: str) -> str:
        """
        Export results with additional metadata to CSV
        
        Args:
            results: List of classification result dictionaries
            metadata: Additional metadata to include
            filename: Filename without extension
            
        Returns:
            Path to exported CSV file
        """
        filepath = os.path.join(self.export_dir, f"{filename}.csv")
        
        # Prepare data with metadata
        csv_rows = []
        for i, result in enumerate(results):
            row = {
                'row_number': i + 1,
                'timestamp': result.get('timestamp', ''),
                'predicted_class': result.get('predicted_class', ''),
                'confidence': result.get('confidence', 0.0),
                'image_included': result.get('image_data') is not None
            }
            
            # Add metadata fields
            for key, value in metadata.items():
                row[f"meta_{key}"] = value
            
            csv_rows.append(row)
        
        # Write to CSV
        df = pd.DataFrame(csv_rows)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        return filepath
    
    def create_summary_report(self, results: List[Dict[str, Any]], filename: str) -> str:
        """
        Create a summary CSV with statistics about the results
        
        Args:
            results: List of classification result dictionaries
            filename: Filename without extension
            
        Returns:
            Path to exported summary CSV file
        """
        filepath = os.path.join(self.export_dir, f"{filename}_summary.csv")
        
        if not results:
            # Empty summary
            summary_data = [{
                'metric': 'total_classifications',
                'value': 0,
                'description': 'No classifications found'
            }]
        else:
            # Calculate statistics
            classes = [r.get('predicted_class', '') for r in results]
            class_counts = {}
            for cls in classes:
                class_counts[cls] = class_counts.get(cls, 0) + 1
            
            # Create summary data
            summary_data = [
                {
                    'metric': 'total_classifications',
                    'value': len(results),
                    'description': 'Total number of classifications'
                },
                {
                    'metric': 'unique_classes',
                    'value': len(class_counts),
                    'description': 'Number of different food classes identified'
                },
                {
                    'metric': 'avg_confidence',
                    'value': sum(r.get('confidence', 0) for r in results) / len(results),
                    'description': 'Average confidence score across all classifications'
                }
            ]
            
            # Add class distribution
            for cls, count in class_counts.items():
                summary_data.append({
                    'metric': f'class_{cls.lower().replace(" ", "_")}_count',
                    'value': count,
                    'description': f'Number of {cls} classifications'
                })
        
        # Write summary to CSV
        df = pd.DataFrame(summary_data)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        return filepath
