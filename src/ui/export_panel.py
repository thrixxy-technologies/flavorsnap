"""
Export Panel - UI component for export functionality
"""

import panel as pn
import os
from typing import Optional, Callable, Dict, Any
from src.utils.export_manager import ExportManager


class ExportPanel:
    """Export interface component for FlavorSnap"""
    
    def __init__(self, on_export_callback: Optional[Callable] = None):
        self.export_manager = ExportManager()
        self.on_export_callback = on_export_callback
        
        # Export format selector
        self.format_selector = pn.widgets.Select(
            name='Export Format',
            options=['CSV', 'JSON', 'PDF', 'Image with Overlay'],
            value='CSV',
            width=200
        )
        
        # Filename input
        self.filename_input = pn.widgets.TextInput(
            name='Filename (optional)',
            placeholder='Leave empty for auto-generated name',
            width=300
        )
        
        # Include image checkbox
        self.include_image_checkbox = pn.widgets.Checkbox(
            name='Include Image in Export',
            value=True
        )
        
        # Export buttons
        self.export_current_button = pn.widgets.Button(
            name='Export Current Result',
            button_type='primary',
            width=200
        )
        
        self.export_batch_button = pn.widgets.Button(
            name='Export Batch Results',
            button_type='success',
            width=200
        )
        
        # Status display
        self.status_display = pn.pane.Markdown("Ready to export", width=400)
        
        # Export history
        self.history_text = pn.pane.TextArea(
            name='Export History',
            height=200,
            width=400,
            disabled=True
        )
        
        # Advanced options
        self.advanced_options = pn.Column(
            pn.widgets.Checkbox(name='Create Summary Report', value=False),
            pn.widgets.Checkbox(name='Include Metadata', value=False),
            pn.widgets.TextInput(name='Custom Metadata (JSON)', placeholder='{"key": "value"}'),
            visible=False
        )
        
        # Toggle advanced options
        self.advanced_toggle = pn.widgets.Button(
            name='Show Advanced Options',
            button_type='light',
            width=200
        )
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Create layout
        self.panel = self._create_layout()
        
        # Update history display
        self._update_history_display()
    
    def _setup_event_handlers(self):
        """Setup event handlers for widgets"""
        self.export_current_button.on_click(self._export_current)
        self.export_batch_button.on_click(self._export_batch)
        self.advanced_toggle.on_click(self._toggle_advanced)
        
        # Update filename hint based on format
        self.format_selector.param.watch(self._update_filename_hint, 'value')
    
    def _create_layout(self) -> pn.Column:
        """Create the export panel layout"""
        return pn.Column(
            "### 📤 Export Options",
            pn.Row(
                self.format_selector,
                self.filename_input
            ),
            self.include_image_checkbox,
            pn.Row(
                self.export_current_button,
                self.export_batch_button
            ),
            self.advanced_toggle,
            self.advanced_options,
            pn.Divider(),
            self.status_display,
            "### 📋 Export History",
            self.history_text,
            width=450,
            margin=(10, 20)
        )
    
    def _export_current(self, event):
        """Handle export of current result"""
        if not self.on_export_callback:
            self.status_display.object = "❌ No export callback provided"
            return
        
        try:
            # Get current classification data from callback
            export_data = self.on_export_callback('get_current_data')
            
            if not export_data:
                self.status_display.object = "❌ No classification result available"
                return
            
            # Prepare export parameters
            export_format = self.format_selector.value.lower()
            filename = self.filename_input.value.strip() or None
            include_image = self.include_image_checkbox.value
            
            # Perform export
            filepath = self.export_manager.export_single_result(
                image=export_data.get('image'),
                predicted_class=export_data.get('predicted_class', ''),
                confidence=export_data.get('confidence', 0.0),
                export_format=export_format,
                filename=filename,
                include_image=include_image
            )
            
            # Handle advanced options
            if self.advanced_options[0].value:  # Create summary report
                self._create_summary_report(export_data, filename)
            
            self.status_display.object = f"✅ Exported successfully: `{os.path.basename(filepath)}`"
            self._update_history_display()
            
            # Notify callback
            if self.on_export_callback:
                self.on_export_callback('export_completed', {'filepath': filepath, 'format': export_format})
                
        except Exception as e:
            self.status_display.object = f"❌ Export failed: {str(e)}"
    
    def _export_batch(self, event):
        """Handle export of batch results"""
        if not self.on_export_callback:
            self.status_display.object = "❌ No export callback provided"
            return
        
        try:
            # Get batch data from callback
            batch_data = self.on_export_callback('get_batch_data')
            
            if not batch_data:
                self.status_display.object = "❌ No batch results available"
                return
            
            # Prepare export parameters
            export_format = self.format_selector.value.lower()
            filename = self.filename_input.value.strip() or None
            
            # Perform export
            filepath = self.export_manager.export_batch_results(
                results=batch_data,
                export_format=export_format,
                filename=filename
            )
            
            # Handle advanced options
            if self.advanced_options[0].value:  # Create summary report
                self._create_batch_summary_report(batch_data, filename)
            
            if self.advanced_options[1].value:  # Include metadata
                metadata = self._parse_metadata()
                if metadata:
                    self._export_with_metadata(batch_data, metadata, filename)
            
            self.status_display.object = f"✅ Batch exported successfully: `{os.path.basename(filepath)}`"
            self._update_history_display()
            
            # Notify callback
            if self.on_export_callback:
                self.on_export_callback('batch_export_completed', {'filepath': filepath, 'format': export_format, 'count': len(batch_data)})
                
        except Exception as e:
            self.status_display.object = f"❌ Batch export failed: {str(e)}"
    
    def _toggle_advanced(self, event):
        """Toggle advanced options visibility"""
        self.advanced_options.visible = not self.advanced_options.visible
        self.advanced_toggle.name = 'Hide Advanced Options' if self.advanced_options.visible else 'Show Advanced Options'
    
    def _update_filename_hint(self, event):
        """Update filename hint based on selected format"""
        format_ext = self.format_selector.value.lower()
        if not self.filename_input.value:
            if format_ext == 'image with overlay':
                self.filename_input.placeholder = 'e.g., flavorsnap_result'
            else:
                self.filename_input.placeholder = f'e.g., flavorsnap_result.{format_ext}'
    
    def _create_summary_report(self, export_data: Dict[str, Any], filename: Optional[str]):
        """Create summary report for current result"""
        try:
            base_filename = filename or f"flavorsnap_summary"
            summary_filepath = self.export_manager.csv_exporter.create_summary_report([export_data], base_filename)
            self.status_display.object += f"\n📊 Summary report created: `{os.path.basename(summary_filepath)}`"
        except Exception as e:
            self.status_display.object += f"\n⚠️ Summary report failed: {str(e)}"
    
    def _create_batch_summary_report(self, batch_data: list, filename: Optional[str]):
        """Create summary report for batch results"""
        try:
            base_filename = filename or f"flavorsnap_batch_summary"
            summary_filepath = self.export_manager.csv_exporter.create_summary_report(batch_data, base_filename)
            self.status_display.object += f"\n📊 Batch summary created: `{os.path.basename(summary_filepath)}`"
        except Exception as e:
            self.status_display.object += f"\n⚠️ Batch summary failed: {str(e)}"
    
    def _parse_metadata(self) -> Optional[Dict[str, Any]]:
        """Parse metadata from input"""
        try:
            metadata_str = self.advanced_options[2].value.strip()
            if not metadata_str:
                return None
            
            import json
            return json.loads(metadata_str)
        except json.JSONDecodeError:
            self.status_display.object = "⚠️ Invalid JSON in metadata field"
            return None
    
    def _export_with_metadata(self, batch_data: list, metadata: Dict[str, Any], filename: Optional[str]):
        """Export with additional metadata"""
        try:
            base_filename = filename or f"flavorsnap_with_metadata"
            export_format = self.format_selector.value.lower()
            
            if export_format == 'csv':
                filepath = self.export_manager.csv_exporter.export_with_metadata(batch_data, metadata, base_filename)
            elif export_format == 'json':
                filepath = self.export_manager.json_exporter.export_with_metadata(batch_data, metadata, base_filename)
            else:
                return  # PDF metadata export not implemented
            
            self.status_display.object += f"\n📋 Metadata export created: `{os.path.basename(filepath)}`"
        except Exception as e:
            self.status_display.object += f"\n⚠️ Metadata export failed: {str(e)}"
    
    def _update_history_display(self):
        """Update the export history display"""
        history = self.export_manager.get_export_history()
        
        if not history:
            self.history_text.value = "No exports yet."
            return
        
        history_text = []
        for i, entry in enumerate(reversed(history[-10:])):  # Show last 10 exports
            timestamp = entry.get('timestamp', '')[:19].replace('T', ' ')
            format_type = entry.get('format', 'unknown')
            filepath = entry.get('filepath', '')
            filename = os.path.basename(filepath) if filepath else 'unknown'
            predicted_class = entry.get('predicted_class', 'N/A')
            
            history_text.append(f"{i+1}. [{timestamp}] {format_type.upper()} - {filename} ({predicted_class})")
        
        self.history_text.value = '\n'.join(history_text)
    
    def get_panel(self) -> pn.Column:
        """Get the export panel widget"""
        return self.panel
    
    def get_supported_formats(self) -> list:
        """Get list of supported export formats"""
        return self.export_manager.get_supported_formats()
    
    def clear_history(self):
        """Clear export history"""
        self.export_manager.clear_export_history()
        self._update_history_display()
        self.status_display.object = "📋 Export history cleared"
    
    def set_current_data(self, image, predicted_class: str, confidence: float = 0.0):
        """Set current classification data for export"""
        self.current_data = {
            'image': image,
            'predicted_class': predicted_class,
            'confidence': confidence,
            'timestamp': pn.state.now if hasattr(pn.state, 'now') else None
        }
    
    def set_batch_data(self, batch_results: list):
        """Set batch results for export"""
        self.batch_data = batch_results
