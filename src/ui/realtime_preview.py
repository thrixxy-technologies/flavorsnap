"""
Real-time Preview Component for FlavorSnap

This module provides real-time preview functionality with before/after comparison,
confidence indicators, and optimization suggestions. It integrates with the debounced
classifier to provide smooth real-time updates during preprocessing adjustments.
"""

import panel as pn
import param
import numpy as np
from PIL import Image
import io
import base64
from typing import Dict, Any, Optional, Callable, List
import sys
from pathlib import Path
import time

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.debounced_classifier import get_debounced_classifier
from src.utils.optimization_suggester import get_optimization_suggestions, OptimizationSuggestion


class RealtimePreview(param.Parameterized):
    """
    Real-time preview component with before/after comparison and confidence tracking.
    
    Features:
    - Before/after image comparison
    - Real-time confidence indicators
    - Optimization suggestions display
    - Performance metrics
    - Toggle for real-time mode
    """
    
    # State parameters
    realtime_enabled = param.Boolean(default=True, doc="Enable real-time preview")
    comparison_mode = param.Selector(objects=['side-by-side', 'slider', 'toggle'], default='side-by-side')
    
    # Image state
    original_image = param.ClassSelector(class_=Image.Image, default=None)
    processed_image = param.ClassSelector(class_=Image.Image, default=None)
    
    # Classification results
    current_result = param.Dict(default={})
    previous_result = param.Dict(default={})
    
    # Optimization suggestions
    optimization_suggestions = param.List(default=[])
    
    # Performance metrics
    processing_time = param.Number(default=0.0)
    confidence_history = param.List(default=[])
    
    def __init__(self, **params):
        super().__init__(**params)
        self.debounced_classifier = get_debounced_classifier()
        self._setup_ui()
        self._setup_callbacks()
    
    def _setup_ui(self):
        """Setup the UI components."""
        # Real-time toggle
        self.realtime_toggle = pn.widgets.Checkbox(
            name='🔄 Real-time Preview',
            value=self.realtime_enabled,
            width=200
        )
        
        # Comparison mode selector
        self.comparison_select = pn.widgets.Select(
            name='Comparison Mode',
            options=['side-by-side', 'slider', 'toggle'],
            value=self.comparison_mode,
            width=200
        )
        
        # Image displays
        self.original_pane = pn.pane.Image(
            width=300, height=300, 
            visible=False,
            css_classes=['original-image']
        )
        
        self.processed_pane = pn.pane.Image(
            width=300, height=300,
            visible=False,
            css_classes=['processed-image']
        )
        
        # Confidence indicators
        self.confidence_bar = pn.widgets.Progress(
            value=0, max=100, width=300,
            bar_color='green',
            css_classes=['confidence-bar']
        )
        
        self.confidence_text = pn.pane.Markdown(
            "### Confidence\nNo data",
            css_classes=['confidence-text']
        )
        
        # Classification result display
        self.result_text = pn.pane.Markdown(
            "### Classification\nWaiting for image...",
            css_classes=['result-text']
        )
        
        # Optimization suggestions
        self.suggestions_text = pn.pane.Markdown(
            "### Optimization Suggestions\nNo suggestions",
            css_classes=['suggestions-text']
        )
        
        # Performance metrics
        self.performance_text = pn.pane.Markdown(
            "### Performance\nReady",
            css_classes=['performance-text']
        )
        
        # Before/After slider for comparison
        self.comparison_slider = pn.widgets.DiscreteSlider(
            name='Before/After',
            options=['Before', 'After'],
            value='After',
            width=300,
            visible=False
        )
        
        # Status indicator
        self.status_indicator = pn.indicators.StatusIndicator(
            value='ready',
            options=['ready', 'processing', 'error'],
            width=20,
            height=20,
            css_classes=['status-indicator']
        )
        
        # Auto-apply suggestions button
        self.auto_apply_button = pn.widgets.Button(
            name='✨ Auto-Apply Suggestions',
            button_type='primary',
            width=200,
            visible=False
        )
        
        # Clear history button
        self.clear_history_button = pn.widgets.Button(
            name='🗑️ Clear History',
            button_type='light',
            width=150
        )
    
    def _setup_callbacks(self):
        """Setup event callbacks."""
        self.realtime_toggle.param.watch(self._on_realtime_toggle, 'value')
        self.comparison_select.param.watch(self._on_comparison_change, 'value')
        self.comparison_slider.param.watch(self._on_comparison_slider_change, 'value')
        self.auto_apply_button.on_click(self._on_auto_apply_suggestions)
        self.clear_history_button.on_click(self._on_clear_history)
    
    def update_image(self, 
                    original_image: Image.Image, 
                    processed_image: Image.Image,
                    preprocessing_params: Optional[Dict[str, Any]] = None):
        """
        Update images and trigger real-time classification.
        
        Args:
            original_image: Original PIL Image
            processed_image: Processed PIL Image
            preprocessing_params: Current preprocessing parameters
        """
        if not self.realtime_enabled:
            return
        
        self.original_image = original_image
        self.processed_image = processed_image
        
        # Update image displays
        self.original_pane.object = original_image
        self.original_pane.visible = True
        self.processed_pane.object = processed_image
        self.processed_pane.visible = True
        
        # Trigger real-time classification
        self._classify_realtime(processed_image, preprocessing_params)
        
        # Update comparison mode visibility
        self._update_comparison_visibility()
    
    def _classify_realtime(self, 
                          image: Image.Image, 
                          preprocessing_params: Optional[Dict[str, Any]] = None):
        """Perform real-time classification with debouncing."""
        if not self.realtime_enabled or not image:
            return
        
        # Update status
        self.status_indicator.value = 'processing'
        
        # Get current confidence for optimization suggestions
        current_confidence = self.current_result.get('confidence', 0.0)
        
        # Get optimization suggestions
        suggestions = get_optimization_suggestions(
            image, preprocessing_params, current_confidence
        )
        self.optimization_suggestions = suggestions
        self._update_suggestions_display()
        
        # Perform debounced classification
        def classification_callback(result):
            self._on_classification_result(result)
        
        self.debounced_classifier.classify_image_debounced(
            image, preprocessing_params, classification_callback
        )
    
    def _on_classification_result(self, result: Dict[str, Any]):
        """Handle classification result."""
        if 'error' in result:
            self.status_indicator.value = 'error'
            self.result_text.object = f"### Error\n{result['error']}"
            return
        
        # Update previous result
        self.previous_result = self.current_result.copy()
        
        # Update current result
        self.current_result = result
        
        # Update UI
        self._update_confidence_display()
        self._update_result_display()
        self._update_performance_display()
        
        # Update status
        self.status_indicator.value = 'ready'
        
        # Update confidence history
        confidence = result.get('confidence', 0.0)
        self.confidence_history.append({
            'timestamp': time.time(),
            'confidence': confidence,
            'predicted_class': result.get('predicted_class', 'Unknown')
        })
        
        # Keep only last 50 entries
        if len(self.confidence_history) > 50:
            self.confidence_history = self.confidence_history[-50:]
    
    def _update_confidence_display(self):
        """Update confidence indicators."""
        confidence = self.current_result.get('confidence', 0.0)
        confidence_percent = confidence * 100
        
        self.confidence_bar.value = confidence_percent
        
        # Determine color based on confidence level
        if confidence >= 0.8:
            bar_color = 'green'
            status_emoji = '🟢'
        elif confidence >= 0.6:
            bar_color = 'orange'
            status_emoji = '🟡'
        else:
            bar_color = 'red'
            status_emoji = '🔴'
        
        self.confidence_bar.bar_color = bar_color
        
        predicted_class = self.current_result.get('predicted_class', 'Unknown')
        self.confidence_text.object = f"""
### Confidence {status_emoji}
**{predicted_class}**: {confidence_percent:.1f}%
        """
    
    def _update_result_display(self):
        """Update classification result display."""
        if not self.current_result:
            return
        
        predicted_class = self.current_result.get('predicted_class', 'Unknown')
        confidence = self.current_result.get('confidence', 0.0)
        confidence_percent = confidence * 100
        
        # Compare with previous result
        confidence_change = 0.0
        if self.previous_result.get('confidence'):
            confidence_change = confidence - self.previous_result['confidence']
            change_emoji = '📈' if confidence_change > 0 else '📉' if confidence_change < 0 else '➡️'
            change_text = f" ({change_emoji} {confidence_change*100:+.1f}%)"
        else:
            change_text = ""
        
        self.result_text.object = f"""
### Classification Result
**{predicted_class}**{change_text}

Confidence: {confidence_percent:.1f}%
        """
    
    def _update_suggestions_display(self):
        """Update optimization suggestions display."""
        if not self.optimization_suggestions:
            self.suggestions_text.object = "### Optimization Suggestions\nNo suggestions"
            self.auto_apply_button.visible = False
            return
        
        # Format suggestions
        suggestions_text = "### Optimization Suggestions\n\n"
        high_priority_count = 0
        
        for i, suggestion in enumerate(self.optimization_suggestions[:5], 1):  # Show top 5
            priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[suggestion.priority]
            impact_emoji = {'significant': '💥', 'moderate': '⚡', 'minimal': '✨'}[suggestion.estimated_impact]
            
            suggestions_text += f"{i}. {priority_emoji} **{suggestion.type.value.title()}** {impact_emoji}\n"
            suggestions_text += f"   - {suggestion.reason}\n"
            suggestions_text += f"   - Estimated improvement: {suggestion.confidence_improvement*100:.1f}%\n\n"
            
            if suggestion.priority == 'high':
                high_priority_count += 1
        
        self.suggestions_text.object = suggestions_text
        self.auto_apply_button.visible = high_priority_count > 0
    
    def _update_performance_display(self):
        """Update performance metrics display."""
        stats = self.debounced_classifier.get_performance_stats()
        
        self.performance_text.object = f"""
### Performance
- **Cache Hit Rate**: {stats['cache_hit_rate']}
- **Avg Processing Time**: {stats['average_processing_time']*1000:.0f}ms
- **Last Processing**: {stats['last_processing_time']*1000:.0f}ms
- **Total Requests**: {stats['total_requests']}
        """
    
    def _update_comparison_visibility(self):
        """Update comparison mode visibility."""
        if self.comparison_mode == 'slider':
            self.comparison_slider.visible = True
        else:
            self.comparison_slider.visible = False
    
    def _on_realtime_toggle(self, event):
        """Handle real-time toggle change."""
        self.realtime_enabled = event.new
        self.debounced_classifier.enable_realtime(self.realtime_enabled)
        
        if not self.realtime_enabled:
            self.status_indicator.value = 'ready'
            self.result_text.object = "### Classification\nReal-time mode disabled"
    
    def _on_comparison_change(self, event):
        """Handle comparison mode change."""
        self.comparison_mode = event.new
        self._update_comparison_visibility()
    
    def _on_comparison_slider_change(self, event):
        """Handle comparison slider change."""
        if event.new == 'Before':
            self.processed_pane.visible = False
            self.original_pane.visible = True
        else:
            self.processed_pane.visible = True
            self.original_pane.visible = self.comparison_mode == 'side-by-side'
    
    def _on_auto_apply_suggestions(self, event):
        """Handle auto-apply suggestions button click."""
        if not self.optimization_suggestions:
            return
        
        # This would integrate with the preprocessing controls
        # For now, just update the display
        applied_count = len([s for s in self.optimization_suggestions if s.priority == 'high'])
        self.suggestions_text.object += f"\n\n✅ Applied {applied_count} high-priority suggestions"
        self.auto_apply_button.visible = False
    
    def _on_clear_history(self, event):
        """Handle clear history button click."""
        self.confidence_history.clear()
        self.previous_result = {}
        self.current_result = {}
        self.optimization_suggestions = []
        
        # Reset displays
        self.confidence_text.object = "### Confidence\nNo data"
        self.result_text.object = "### Classification\nWaiting for image..."
        self.suggestions_text.object = "### Optimization Suggestions\nNo suggestions"
        self.confidence_bar.value = 0
    
    def get_confidence_trend(self) -> str:
        """Get confidence trend analysis."""
        if len(self.confidence_history) < 2:
            return "Insufficient data"
        
        recent_confidences = [entry['confidence'] for entry in self.confidence_history[-10:]]
        avg_recent = np.mean(recent_confidences)
        
        if len(self.confidence_history) >= 10:
            earlier_confidences = [entry['confidence'] for entry in self.confidence_history[-20:-10]]
            avg_earlier = np.mean(earlier_confidences)
            
            if avg_recent > avg_earlier + 0.05:
                return "📈 Improving"
            elif avg_recent < avg_earlier - 0.05:
                return "📉 Declining"
        
        return "➡️ Stable"
    
    def create_layout(self) -> pn.Column:
        """Create the main layout for the real-time preview component."""
        # Header with controls
        header = pn.Row(
            self.realtime_toggle,
            self.comparison_select,
            self.status_indicator,
            spacing=10
        )
        
        # Image comparison section
        if self.comparison_mode == 'side-by-side':
            image_section = pn.Row(
                pn.Column("### Before", self.original_pane),
                pn.Column("### After", self.processed_pane),
                spacing=10
            )
        else:
            image_section = pn.Column(
                self.comparison_slider,
                self.original_pane,
                self.processed_pane,
                spacing=10
            )
        
        # Results section
        results_section = pn.Column(
            self.confidence_bar,
            self.confidence_text,
            self.result_text,
            spacing=10
        )
        
        # Suggestions section
        suggestions_section = pn.Column(
            pn.Row(self.auto_apply_button, self.clear_history_button, spacing=10),
            self.suggestions_text,
            spacing=10
        )
        
        # Performance section
        performance_section = pn.Column(
            self.performance_text,
            spacing=10
        )
        
        # Main layout
        layout = pn.Column(
            pn.pane.Markdown("## 🔄 Real-time Preview"),
            header,
            image_section,
            pn.layout.Divider(),
            results_section,
            pn.layout.Divider(),
            suggestions_section,
            pn.layout.Divider(),
            performance_section,
            sizing_mode='stretch_width',
            max_width=800,
            css_classes=['realtime-preview']
        )
        
        return layout


def create_realtime_preview_panel() -> pn.Column:
    """Create a real-time preview panel."""
    preview = RealtimePreview()
    return preview.create_layout()
