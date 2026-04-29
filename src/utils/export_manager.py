"""
Export Manager - Centralized export functionality for FlavorSnap classification results
"""

import os
import json
import csv
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from PIL import Image
import io

from src.export.csv_exporter import CSVExporter
from src.export.json_exporter import JSONExporter
from src.export.pdf_exporter import PDFExporter


class ExportManager:
    """Manages all export operations for classification results"""
    
    def __init__(self):
        self.csv_exporter = CSVExporter()
        self.json_exporter = JSONExporter()
        self.pdf_exporter = PDFExporter()
        self.export_history = []
        
    def export_single_result(self, 
                           image: Image.Image, 
                           predicted_class: str, 
                           confidence: float = 0.0,
                           export_format: str = "csv",
                           filename: Optional[str] = None,
                           include_image: bool = True) -> str:
        """
        Export a single classification result
        
        Args:
            image: PIL Image object
            predicted_class: Predicted food class
            confidence: Confidence score (0.0-1.0)
            export_format: Format to export ('csv', 'json', 'pdf', 'image')
            filename: Custom filename (without extension)
            include_image: Whether to include image in export
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flavorsnap_{predicted_class}_{timestamp}"
        
        result_data = {
            'timestamp': datetime.now().isoformat(),
            'predicted_class': predicted_class,
            'confidence': confidence,
            'image_data': image if include_image else None
        }
        
        if export_format.lower() == 'csv':
            return self.csv_exporter.export_single(result_data, filename)
        elif export_format.lower() == 'json':
            return self.json_exporter.export_single(result_data, filename)
        elif export_format.lower() == 'pdf':
            return self.pdf_exporter.export_single(result_data, filename)
        elif export_format.lower() == 'image':
            return self._export_image_with_overlay(image, predicted_class, confidence, filename)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    def export_batch_results(self, 
                           results: List[Dict[str, Any]], 
                           export_format: str = "csv",
                           filename: Optional[str] = None) -> str:
        """
        Export multiple classification results
        
        Args:
            results: List of classification result dictionaries
            export_format: Format to export ('csv', 'json', 'pdf')
            filename: Custom filename (without extension)
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flavorsnap_batch_{timestamp}"
        
        if export_format.lower() == 'csv':
            return self.csv_exporter.export_batch(results, filename)
        elif export_format.lower() == 'json':
            return self.json_exporter.export_batch(results, filename)
        elif export_format.lower() == 'pdf':
            return self.pdf_exporter.export_batch(results, filename)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    def _export_image_with_overlay(self, 
                                 image: Image.Image, 
                                 predicted_class: str, 
                                 confidence: float,
                                 filename: str) -> str:
        """Export image with classification overlay"""
        from PIL import ImageDraw, ImageFont
        
        # Create a copy to avoid modifying original
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Add semi-transparent overlay at bottom
        overlay_height = 80
        overlay = Image.new('RGBA', (img_copy.width, overlay_height), (0, 0, 0, 180))
        img_copy.paste(overlay, (0, img_copy.height - overlay_height), overlay)
        
        # Add text
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        text_lines = [
            f"Class: {predicted_class}",
            f"Confidence: {confidence:.2%}"
        ]
        
        y_position = img_copy.height - overlay_height + 10
        for line in text_lines:
            draw.text((10, y_position), line, fill=(255, 255, 255), font=font)
            y_position += 30
        
        # Save
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)
        
        filepath = os.path.join(export_dir, f"{filename}.png")
        img_copy.save(filepath, "PNG")
        
        # Record in history
        self.export_history.append({
            'timestamp': datetime.now().isoformat(),
            'format': 'image',
            'filepath': filepath,
            'predicted_class': predicted_class
        })
        
        return filepath
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """Get history of all exports"""
        return self.export_history.copy()
    
    def clear_export_history(self):
        """Clear export history"""
        self.export_history.clear()
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats"""
        return ['csv', 'json', 'pdf', 'image']
