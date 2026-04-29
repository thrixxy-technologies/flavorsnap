"""
Preprocessing Controls UI Component for FlavorSnap

This module provides the Panel-based UI components for real-time image preprocessing controls.
"""

import panel as pn
import param
import numpy as np
from PIL import Image
import io
import base64
from typing import Callable, Optional, Dict, Any
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.image_enhancer import ImageEnhancer
from src.utils.optimization_suggester import get_optimization_suggestions


class PreprocessingControls(param.Parameterized):
    """Panel component for image preprocessing controls."""
    
    # Image enhancer instance
    enhancer = param.ClassSelector(class_=ImageEnhancer, default=None)
    
    # Control parameters
    brightness = param.Number(default=1.0, bounds=(0.0, 2.0), step=0.1)
    contrast = param.Number(default=1.0, bounds=(0.0, 2.0), step=0.1)
    rotation = param.Number(default=0.0, bounds=(-180, 180), step=1)
    aspect_ratio = param.Selector(objects=['Original', '1:1', '4:3', '16:9', '3:2', '9:16'], default='Original')
    
    # Callbacks
    on_image_update = param.Callable(default=None)
    on_realtime_update = param.Callable(default=None)  # New callback for real-time updates
    
    def __init__(self, **params):
        super().__init__(**params)
        self.enhancer = ImageEnhancer()
        self.original_image = None
        self.current_image = None
        self._setup_controls()
    
    def _setup_controls(self):
        """Setup the control widgets."""
        # Brightness slider
        self.brightness_slider = pn.widgets.FloatSlider(
            name='Brightness',
            start=0.0,
            end=2.0,
            step=0.1,
            value=1.0,
            width=300
        )
        
        # Contrast slider
        self.contrast_slider = pn.widgets.FloatSlider(
            name='Contrast',
            start=0.0,
            end=2.0,
            step=0.1,
            value=1.0,
            width=300
        )
        
        # Rotation slider
        self.rotation_slider = pn.widgets.FloatSlider(
            name='Rotation (degrees)',
            start=-180,
            end=180,
            step=1,
            value=0.0,
            width=300
        )
        
        # Aspect ratio selector
        self.aspect_ratio_select = pn.widgets.Select(
            name='Aspect Ratio',
            options=['Original', '1:1', '4:3', '16:9', '3:2', '9:16'],
            value='Original',
            width=300
        )
        
        # Buttons
        self.reset_button = pn.widgets.Button(
            name='🔄 Reset',
            button_type='default',
            width=100
        )
        
        self.auto_enhance_button = pn.widgets.Button(
            name='✨ Auto Enhance',
            button_type='primary',
            width=120
        )
        
        # Crop controls
        self.crop_enabled = pn.widgets.Checkbox(
            name='Enable Crop',
            value=False
        )
        
        self.crop_x = pn.widgets.IntSlider(
            name='Crop X',
            start=0,
            end=100,
            value=0,
            width=200
        )
        
        self.crop_y = pn.widgets.IntSlider(
            name='Crop Y',
            start=0,
            end=100,
            value=0,
            width=200
        )
        
        self.crop_width = pn.widgets.IntSlider(
            name='Crop Width',
            start=10,
            end=100,
            value=100,
            width=200
        )
        
        self.crop_height = pn.widgets.IntSlider(
            name='Crop Height',
            start=10,
            end=100,
            value=100,
            width=200
        )
        
        # Status display
        self.status_text = pn.pane.Markdown("### Status\nReady to process image")
        
        # Parameters display
        self.params_text = pn.pane.Markdown("### Current Parameters\nNo image loaded")
        
        # Real-time toggle
        self.realtime_toggle = pn.widgets.Checkbox(
            name='🔄 Real-time Updates',
            value=True,
            width=200
        )
        
        # Optimization suggestions display
        self.suggestions_text = pn.pane.Markdown("### 💡 Optimization Suggestions\nNo image loaded")
        
        # Auto-apply suggestions button
        self.auto_apply_button = pn.widgets.Button(
            name='✨ Auto-Apply',
            button_type='primary',
            width=120,
            visible=False
        )
        
        # Setup event handlers
        self.brightness_slider.param.watch(self._on_brightness_change, 'value')
        self.contrast_slider.param.watch(self._on_contrast_change, 'value')
        self.rotation_slider.param.watch(self._on_rotation_change, 'value')
        self.aspect_ratio_select.param.watch(self._on_aspect_ratio_change, 'value')
        self.reset_button.on_click(self._on_reset)
        self.auto_enhance_button.on_click(self._on_auto_enhance)
        self.crop_enabled.param.watch(self._on_crop_toggle, 'value')
        self.crop_x.param.watch(self._on_crop_change, 'value')
        self.crop_y.param.watch(self._on_crop_change, 'value')
        self.crop_width.param.watch(self._on_crop_change, 'value')
        self.crop_height.param.watch(self._on_crop_change, 'value')
        
        # Real-time and optimization handlers
        self.realtime_toggle.param.watch(self._on_realtime_toggle, 'value')
        self.auto_apply_button.on_click(self._on_auto_apply_suggestions)
    
    def load_image(self, image: Image.Image) -> None:
        """Load an image for preprocessing."""
        self.original_image = image
        self.enhancer.load_image(image)
        self.current_image = image
        
        # Update crop sliders based on image dimensions
        width, height = image.size
        self.crop_x.end = width - 1
        self.crop_y.end = height - 1
        self.crop_width.end = width
        self.crop_height.end = height
        
        # Reset controls
        self._reset_controls()
        
        # Update status
        self._update_status("Image loaded successfully")
        self._update_parameters()
        
        # Generate optimization suggestions
        self._update_optimization_suggestions()
    
    def _on_brightness_change(self, event):
        """Handle brightness change."""
        if self.original_image:
            self._apply_enhancements()
    
    def _on_contrast_change(self, event):
        """Handle contrast change."""
        if self.original_image:
            self._apply_enhancements()
    
    def _on_rotation_change(self, event):
        """Handle rotation change."""
        if self.original_image:
            self._apply_enhancements()
    
    def _on_aspect_ratio_change(self, event):
        """Handle aspect ratio change."""
        if self.original_image and event.new != 'Original':
            self.enhancer.apply_aspect_ratio_crop(event.new)
            self.current_image = self.enhancer.get_processed_image()
            self._notify_update()
            self._update_status(f"Applied {event.new} aspect ratio")
        elif event.new == 'Original' and self.original_image:
            self._reset_to_original()
    
    def _on_crop_change(self, event):
        """Handle crop parameter change."""
        if self.original_image and self.crop_enabled.value:
            x = self.crop_x.value
            y = self.crop_y.value
            w = self.crop_width.value
            h = self.crop_height.value
            
            crop_box = (x, y, x + w, y + h)
            self.enhancer.load_image(self.original_image)
            
            # Apply other enhancements first
            self.enhancer.apply_brightness(self.brightness_slider.value)
            self.enhancer.apply_contrast(self.contrast_slider.value)
            self.enhancer.apply_rotation(self.rotation_slider.value)
            
            # Apply crop last
            self.enhancer.apply_crop(crop_box)
            self.current_image = self.enhancer.get_processed_image()
            self._notify_update()
            self._update_status(f"Crop applied: {crop_box}")
    
    def _on_crop_toggle(self, event):
        """Handle crop enable/disable."""
        if event.new and self.original_image:
            self._apply_enhancements()
        elif not event.new and self.original_image:
            self._reset_to_original()
    
    def _on_reset(self, event):
        """Handle reset button click."""
        if self.original_image:
            self._reset_controls()
            self.enhancer.reset_parameters()
            self.current_image = self.original_image
            self._notify_update()
            self._update_status("Reset to original image")
            self._update_parameters()
    
    def _on_auto_enhance(self, event):
        """Handle auto enhance button click."""
        if self.original_image:
            self.enhancer.load_image(self.original_image)
            enhanced = self.enhancer.auto_enhance()
            self.current_image = enhanced
            
            # Update sliders to reflect auto-enhancement
            params = self.enhancer.get_enhancement_params()
            self.brightness_slider.value = params.get('brightness', 1.0)
            self.contrast_slider.value = params.get('contrast', 1.0)
            
            self._notify_update()
            self._update_status("Auto enhancement applied")
            self._update_parameters()
    
    def _apply_enhancements(self):
        """Apply all current enhancements."""
        if not self.original_image:
            return
        
        self.enhancer.load_image(self.original_image)
        
        # Apply enhancements in order
        self.enhancer.apply_brightness(self.brightness_slider.value)
        self.enhancer.apply_contrast(self.contrast_slider.value)
        self.enhancer.apply_rotation(self.rotation_slider.value)
        
        # Apply crop if enabled
        if self.crop_enabled.value:
            x = self.crop_x.value
            y = self.crop_y.value
            w = self.crop_width.value
            h = self.crop_height.value
            crop_box = (x, y, x + w, y + h)
            self.enhancer.apply_crop(crop_box)
        
        # Apply aspect ratio if selected
        if self.aspect_ratio_select.value != 'Original':
            self.enhancer.apply_aspect_ratio_crop(self.aspect_ratio_select.value)
        
        self.current_image = self.enhancer.get_processed_image()
        self._notify_update()
        self._update_status("Enhancements applied")
        self._update_parameters()
        
        # Trigger real-time update if enabled
        if self.realtime_toggle.value and self.on_realtime_update:
            preprocessing_params = self.get_enhancement_params()
            self.on_realtime_update(self.current_image, preprocessing_params)
    
    def _reset_to_original(self):
        """Reset to original image."""
        self.current_image = self.original_image
        self._notify_update()
    
    def _reset_controls(self):
        """Reset all controls to default values."""
        self.brightness_slider.value = 1.0
        self.contrast_slider.value = 1.0
        self.rotation_slider.value = 0.0
        self.aspect_ratio_select.value = 'Original'
        self.crop_enabled.value = False
        self.crop_x.value = 0
        self.crop_y.value = 0
        self.crop_width.value = 100
        self.crop_height.value = 100
    
    def _notify_update(self):
        """Notify that image has been updated."""
        if self.on_image_update:
            self.on_image_update(self.current_image)
    
    def _update_status(self, message: str):
        """Update status display."""
        self.status_text.object = f"### Status\n{message}"
    
    def _update_parameters(self):
        """Update parameters display."""
        if not self.original_image:
            self.params_text.object = "### Current Parameters\nNo image loaded"
            return
        
        params = self.enhancer.get_enhancement_params()
        img_info = self.enhancer.get_image_info()
        
        params_str = f"""
### Current Parameters
- **Brightness**: {params['brightness']:.1f}
- **Contrast**: {params['contrast']:.1f}
- **Rotation**: {params['rotation']:.0f}°
- **Aspect Ratio**: {params.get('aspect_ratio', 'Original')}
- **Crop**: {params.get('crop_box', 'None')}

### Image Info
- **Size**: {img_info.get('width', 0)} × {img_info.get('height', 0)}
- **Aspect Ratio**: {img_info.get('aspect_ratio', 0):.2f}
        """
        self.params_text.object = params_str
    
    def get_processed_image(self) -> Optional[Image.Image]:
        """Get the current processed image."""
        return self.current_image
    
    def get_enhancement_params(self) -> Dict[str, Any]:
        """Get current enhancement parameters."""
        return self.enhancer.get_enhancement_params()
    
    def _on_realtime_toggle(self, event):
        """Handle real-time toggle change."""
        enabled = event.new
        status = "enabled" if enabled else "disabled"
        self._update_status(f"Real-time updates {status}")
        
        # Trigger update if enabling and image is loaded
        if enabled and self.current_image and self.on_realtime_update:
            preprocessing_params = self.get_enhancement_params()
            self.on_realtime_update(self.current_image, preprocessing_params)
    
    def _update_optimization_suggestions(self):
        """Update optimization suggestions based on current image."""
        if not self.original_image:
            return
        
        try:
            current_params = self.get_enhancement_params()
            suggestions = get_optimization_suggestions(self.original_image, current_params)
            
            if suggestions:
                suggestions_text = "### 💡 Optimization Suggestions\n\n"
                high_priority_count = 0
                
                for i, suggestion in enumerate(suggestions[:5], 1):  # Show top 5
                    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[suggestion.priority]
                    impact_emoji = {'significant': '💥', 'moderate': '⚡', 'minimal': '✨'}[suggestion.estimated_impact]
                    
                    suggestions_text += f"{i}. {priority_emoji} **{suggestion.type.value.title()}** {impact_emoji}\n"
                    suggestions_text += f"   - {suggestion.reason}\n"
                    suggestions_text += f"   - Est. improvement: {suggestion.confidence_improvement*100:.1f}%\n\n"
                    
                    if suggestion.priority == 'high':
                        high_priority_count += 1
                
                self.suggestions_text.object = suggestions_text
                self.auto_apply_button.visible = high_priority_count > 0
            else:
                self.suggestions_text.object = "### 💡 Optimization Suggestions\n\nNo suggestions - image looks good!"
                self.auto_apply_button.visible = False
                
        except Exception as e:
            self.suggestions_text.object = f"### 💡 Optimization Suggestions\n\nError generating suggestions: {str(e)}"
            self.auto_apply_button.visible = False
    
    def _on_auto_apply_suggestions(self, event):
        """Handle auto-apply suggestions button click."""
        if not self.original_image:
            return
        
        try:
            current_params = self.get_enhancement_params()
            suggestions = get_optimization_suggestions(self.original_image, current_params)
            
            # Apply high-priority suggestions
            applied_count = 0
            for suggestion in suggestions:
                if suggestion.priority == 'high':
                    if hasattr(self, f"_{suggestion.type.value}_slider"):
                        slider = getattr(self, f"_{suggestion.type.value}_slider")
                        slider.value = suggestion.suggested_value
                        applied_count += 1
                    elif suggestion.type.value == 'aspect_ratio':
                        self.aspect_ratio_select.value = suggestion.suggested_value
                        applied_count += 1
            
            # Update suggestions after applying
            self._update_optimization_suggestions()
            
            # Show feedback
            self._update_status(f"Applied {applied_count} high-priority suggestions")
            
        except Exception as e:
            self._update_status(f"Error applying suggestions: {str(e)}")
    
    def set_realtime_callback(self, callback: Callable):
        """Set the real-time update callback."""
        self.on_realtime_update = callback
    
    def is_realtime_enabled(self) -> bool:
        """Check if real-time updates are enabled."""
        return self.realtime_toggle.value
    
    def create_layout(self) -> pn.Column:
        """Create the Panel layout for the controls."""
        # Basic adjustments
        basic_controls = pn.Column(
            pn.pane.Markdown("### 🎨 Basic Adjustments"),
            self.brightness_slider,
            self.contrast_slider,
            self.rotation_slider,
            self.aspect_ratio_select,
            spacing=10
        )
        
        # Crop controls
        crop_controls = pn.Column(
            pn.pane.Markdown("### ✂️ Crop Controls"),
            self.crop_enabled,
            self.crop_x,
            self.crop_y,
            self.crop_width,
            self.crop_height,
            spacing=10
        )
        
        # Action buttons
        action_buttons = pn.Row(
            self.reset_button,
            self.auto_enhance_button,
            self.auto_apply_button,
            spacing=10
        )
        
        # Real-time controls
        realtime_controls = pn.Column(
            pn.pane.Markdown("### 🔄 Real-time Settings"),
            self.realtime_toggle,
            spacing=10
        )
        
        # Status and info
        info_panel = pn.Column(
            self.status_text,
            self.params_text,
            spacing=10
        )
        
        # Suggestions panel
        suggestions_panel = pn.Column(
            self.suggestions_text,
            spacing=10
        )
        
        # Main layout
        layout = pn.Column(
            pn.pane.Markdown("## 🖼️ Image Preprocessing Controls"),
            realtime_controls,
            basic_controls,
            crop_controls,
            action_buttons,
            suggestions_panel,
            info_panel,
            sizing_mode='stretch_width',
            max_width=450
        )
        
        return layout


def create_preprocessing_panel(on_image_update: Callable = None) -> pn.Column:
    """Create a preprocessing panel with optional callback."""
    controls = PreprocessingControls(on_image_update=on_image_update)
    return controls.create_layout()
