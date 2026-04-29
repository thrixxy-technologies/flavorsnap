"""
Visualization module for model explainability.

Provides comprehensive visualization capabilities for SHAP, LIME, Grad-CAM,
and other XAI methods with performance optimization.
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
from PIL import Image
import cv2
import base64
import io
import warnings
from typing import Dict, List, Tuple, Any, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from skimage.segmentation import mark_boundaries
import plotly.io as pio

warnings.filterwarnings('ignore')

class XAIVisualizer:
    """Comprehensive visualization class for model explainability"""
    
    def __init__(self):
        """Initialize the XAI visualizer"""
        # Set matplotlib backend for better performance
        plt.switch_backend('Agg')
        
        # Set default style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Configure plotly
        pio.kaleido.scope.mathjax = False
        
    def create_feature_importance_plot(self, importance_dict: Dict[str, float], 
                                     title: str = "Feature Importance",
                                     method: str = "SHAP") -> str:
        """
        Create feature importance visualization
        
        Args:
            importance_dict: Dictionary of feature names and importance scores
            title: Plot title
            method: XAI method name (SHAP, LIME, etc.)
            
        Returns:
            Base64 encoded image string
        """
        try:
            # Sort features by importance
            sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
            features, values = zip(*sorted_features[:20])  # Top 20 features
            
            # Create figure
            plt.figure(figsize=(12, 8))
            
            # Create horizontal bar plot
            bars = plt.barh(range(len(features)), values, color=plt.cm.viridis(np.linspace(0, 1, len(features))))
            
            # Customize plot
            plt.yticks(range(len(features)), [f.replace('_', ' ').title() for f in features])
            plt.xlabel('Importance Score')
            plt.title(f'{title} - {method} Analysis', fontsize=16, fontweight='bold')
            
            # Add value labels on bars
            for i, (bar, value) in enumerate(zip(bars, values)):
                plt.text(value + 0.001, bar.get_y() + bar.get_height()/2, 
                        f'{value:.3f}', ha='left', va='center', fontsize=10)
            
            # Add grid
            plt.grid(axis='x', alpha=0.3)
            
            # Adjust layout
            plt.tight_layout()
            
            # Save to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150, facecolor='white')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error creating feature importance plot: {e}")
            return ""
    
    def create_comparison_plot(self, explanations: Dict[str, Dict], 
                             image: np.ndarray = None) -> str:
        """
        Create comparison plot for multiple XAI methods
        
        Args:
            explanations: Dictionary containing explanations from different methods
            image: Original image (optional)
            
        Returns:
            Base64 encoded image string
        """
        try:
            num_methods = len(explanations)
            if num_methods == 0:
                return ""
            
            # Calculate subplot grid
            cols = min(3, num_methods + 1)  # +1 for original image
            rows = (num_methods + 1 + cols - 1) // cols
            
            fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
            if rows == 1 and cols == 1:
                axes = [axes]
            elif rows == 1:
                axes = axes
            else:
                axes = axes.flatten()
            
            # Plot original image if provided
            if image is not None:
                axes[0].imshow(image)
                axes[0].set_title('Original Image', fontsize=14, fontweight='bold')
                axes[0].axis('off')
                start_idx = 1
            else:
                start_idx = 0
            
            # Plot each explanation method
            for i, (method_name, explanation) in enumerate(explanations.items()):
                ax_idx = start_idx + i
                
                if ax_idx >= len(axes):
                    break
                
                # Handle different explanation types
                if 'heatmap_overlay' in explanation:
                    # Grad-CAM or similar overlay
                    img_data = explanation['heatmap_overlay']
                    if img_data.startswith('data:image'):
                        # Decode base64 image
                        import re
                        base64_data = re.sub(r'^data:image/.+;base64,', '', img_data)
                        img_bytes = base64.b64decode(base64_data)
                        img = Image.open(io.BytesIO(img_bytes))
                        axes[ax_idx].imshow(img)
                    else:
                        axes[ax_idx].text(0.5, 0.5, f'{method_name}\n(Visualization)', 
                                        ha='center', va='center', transform=axes[ax_idx].transAxes)
                
                elif 'feature_importance' in explanation:
                    # Feature importance plot
                    importance = explanation['feature_importance']
                    if importance:
                        sorted_items = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]
                        features, values = zip(*sorted_items)
                        axes[ax_idx].barh(range(len(features)), values)
                        axes[ax_idx].set_yticks(range(len(features)))
                        axes[ax_idx].set_yticklabels([f.replace('_', ' ').title() for f in features])
                        axes[ax_idx].set_xlabel('Importance')
                
                else:
                    # Generic explanation text
                    explanation_text = explanation.get('explanation', f'{method_name} explanation')
                    axes[ax_idx].text(0.05, 0.95, explanation_text, 
                                    ha='left', va='top', transform=axes[ax_idx].transAxes,
                                    wrap=True, fontsize=10)
                
                axes[ax_idx].set_title(f'{method_name}', fontsize=12, fontweight='bold')
                axes[ax_idx].axis('off')
            
            # Hide unused subplots
            for i in range(start_idx + len(explanations), len(axes)):
                axes[i].axis('off')
            
            plt.tight_layout()
            
            # Save to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150, facecolor='white')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error creating comparison plot: {e}")
            return ""
    
    def create_interactive_shap_plot(self, shap_values: np.ndarray, 
                                   image: np.ndarray) -> str:
        """
        Create interactive SHAP visualization using Plotly
        
        Args:
            shap_values: SHAP values array
            image: Original image
            
        Returns:
            HTML string for interactive plot
        """
        try:
            # Create subplot
            fig = make_subplots(
                rows=1, cols=3,
                subplot_titles=('Original Image', 'SHAP Values', 'Combined'),
                specs=[[{"type": "image"}, {"type": "heatmap"}, {"type": "image"}]]
            )
            
            # Original image
            fig.add_trace(
                go.Image(z=image),
                row=1, col=1
            )
            
            # SHAP values heatmap
            if len(shap_values.shape) == 3:
                shap_abs = np.mean(np.abs(shap_values), axis=2)
            else:
                shap_abs = np.abs(shap_values)
            
            fig.add_trace(
                go.Heatmap(z=shap_abs, colorscale='RdBu', showscale=True),
                row=1, col=2
            )
            
            # Combined visualization
            combined = image.copy()
            if len(shap_values.shape) == 3:
                shap_overlay = np.mean(np.abs(shap_values), axis=2)
                if len(combined.shape) == 3:
                    combined[:, :, 0] = np.clip(combined[:, :, 0] + shap_overlay * 0.5, 0, 1)
            
            fig.add_trace(
                go.Image(z=combined),
                row=1, col=3
            )
            
            # Update layout
            fig.update_layout(
                title='Interactive SHAP Explanation',
                height=400,
                showlegend=False
            )
            
            # Convert to HTML
            html_str = fig.to_html(include_plotlyjs='cdn')
            
            return html_str
            
        except Exception as e:
            print(f"Error creating interactive SHAP plot: {e}")
            return ""
    
    def create_confidence_visualization(self, confidence_data: Dict[str, Any]) -> str:
        """
        Create confidence visualization
        
        Args:
            confidence_data: Dictionary containing confidence information
            
        Returns:
            Base64 encoded image string
        """
        try:
            predictions = confidence_data.get('predictions', [])
            if not predictions:
                return ""
            
            # Extract data
            classes = [pred['class'] for pred in predictions]
            confidences = [pred['confidence'] for pred in predictions]
            percentages = [pred['percentage'] for pred in predictions]
            
            # Create figure
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Bar plot of confidences
            bars = ax1.bar(range(len(classes)), confidences, 
                          color=plt.cm.Set2(np.linspace(0, 1, len(classes))))
            
            # Customize bar plot
            ax1.set_xlabel('Predicted Classes')
            ax1.set_ylabel('Confidence Score')
            ax1.set_title('Model Prediction Confidence', fontsize=14, fontweight='bold')
            ax1.set_xticks(range(len(classes)))
            ax1.set_xticklabels([cls[:15] + '...' if len(cls) > 15 else cls for cls in classes], 
                               rotation=45, ha='right')
            
            # Add value labels on bars
            for i, (bar, conf) in enumerate(zip(bars, confidences)):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                        f'{conf:.2f}', ha='center', va='bottom', fontsize=10)
            
            # Pie chart of confidence distribution
            colors = plt.cm.Set3(np.linspace(0, 1, len(classes)))
            wedges, texts, autotexts = ax2.pie(confidences, labels=classes, autopct='%1.1f%%',
                                              colors=colors, startangle=90)
            
            # Customize pie chart
            ax2.set_title('Confidence Distribution', fontsize=14, fontweight='bold')
            
            # Make percentage text more readable
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            # Add overall confidence info
            overall_conf = confidence_data.get('overall_confidence', 0)
            entropy = confidence_data.get('entropy', 0)
            certainty = confidence_data.get('certainty', 'unknown')
            
            fig.suptitle(f'Overall Confidence: {overall_conf:.2f} | Entropy: {entropy:.2f} | Certainty: {certainty}',
                        fontsize=16, fontweight='bold')
            
            plt.tight_layout()
            
            # Save to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150, facecolor='white')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error creating confidence visualization: {e}")
            return ""
    
    def create_model_interpretation_dashboard(self, explanations: Dict[str, Dict],
                                           prediction_info: Dict[str, Any]) -> str:
        """
        Create comprehensive model interpretation dashboard
        
        Args:
            explanations: Dictionary of explanations from different XAI methods
            prediction_info: Dictionary containing prediction information
            
        Returns:
            HTML string for interactive dashboard
        """
        try:
            # Create figure with subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=('Prediction Confidence', 'Feature Importance Comparison',
                              'Method Comparison', 'Model Interpretation Summary',
                              'Decision Process', 'Recommendations'),
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "scatter"}, {"type": "table"}],
                       [{"type": "pie"}, {"type": "indicator"}]]
            )
            
            # 1. Prediction Confidence
            if 'confidence_explanation' in explanations:
                conf_data = explanations['confidence_explanation']
                predictions = conf_data.get('predictions', [])
                if predictions:
                    classes = [pred['class'][:10] for pred in predictions]
                    confidences = [pred['confidence'] for pred in predictions]
                    
                    fig.add_trace(
                        go.Bar(x=classes, y=confidences, name='Confidence'),
                        row=1, col=1
                    )
            
            # 2. Feature Importance Comparison
            methods_with_importance = []
            for method, data in explanations.items():
                if 'feature_importance' in data and data['feature_importance']:
                    methods_with_importance.append((method, data['feature_importance']))
            
            if methods_with_importance:
                for i, (method, importance) in enumerate(methods_with_importance[:3]):  # Top 3 methods
                    sorted_items = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
                    features = [f[:8] for f, _ in sorted_items]
                    values = [v for _, v in sorted_items]
                    
                    fig.add_trace(
                        go.Bar(x=features, y=values, name=method),
                        row=1, col=2
                    )
            
            # 3. Method Comparison (Radar chart style)
            methods = list(explanations.keys())
            scores = []
            
            for method in methods:
                # Calculate a simple effectiveness score based on available data
                data = explanations[method]
                score = 0
                
                if 'feature_importance' in data and data['feature_importance']:
                    score += 3
                if 'explanation' in data and len(data['explanation']) > 50:
                    score += 2
                if any(key in data for key in ['shap_image', 'lime_image', 'heatmap_overlay']):
                    score += 3
                
                scores.append(score)
            
            fig.add_trace(
                go.Scatterpolar(r=scores, theta=methods, fill='toself', name='Method Effectiveness'),
                row=2, col=1
            )
            
            # 4. Model Interpretation Summary Table
            summary_data = []
            for method, data in explanations.items():
                summary_data.append([
                    method,
                    "✓" if 'feature_importance' in data else "✗",
                    "✓" if any(key in data for key in ['shap_image', 'lime_image', 'heatmap_overlay']) else "✗",
                    "✓" if 'explanation' in data else "✗",
                    len(str(data.get('explanation', '')))
                ])
            
            fig.add_trace(
                go.Table(
                    header=dict(values=['Method', 'Features', 'Visualization', 'Explanation', 'Detail Level']),
                    cells=dict(values=list(zip(*summary_data)) if summary_data else [[], [], [], [], []])
                ),
                row=2, col=2
            )
            
            # 5. Decision Process (Pie chart)
            if predictions:
                fig.add_trace(
                    go.Pie(labels=classes, values=confidences, name="Decision Distribution"),
                    row=3, col=1
                )
            
            # 6. Recommendations (Gauge chart)
            overall_confidence = prediction_info.get('confidence', 0.5)
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=overall_confidence * 100,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Model Confidence"},
                    gauge={'axis': {'range': [None, 100]},
                          'bar': {'color': "darkblue"},
                          'steps': [
                              {'range': [0, 50], 'color': "lightgray"},
                              {'range': [50, 80], 'color': "gray"}],
                          'threshold': {'line': {'color': "red", 'width': 4},
                                      'thickness': 0.75, 'value': 90}}
                ),
                row=3, col=2
            )
            
            # Update layout
            fig.update_layout(
                title='Model Interpretation Dashboard',
                height=1200,
                showlegend=True
            )
            
            # Convert to HTML
            html_str = fig.to_html(include_plotlyjs='cdn')
            
            return html_str
            
        except Exception as e:
            print(f"Error creating interpretation dashboard: {e}")
            return ""
    
    def create_performance_optimization_visualization(self, performance_data: Dict[str, Any]) -> str:
        """
        Create visualization for performance optimization metrics
        
        Args:
            performance_data: Dictionary containing performance metrics
            
        Returns:
            Base64 encoded image string
        """
        try:
            methods = list(performance_data.keys())
            times = [performance_data[method].get('time', 0) for method in methods]
            memory = [performance_data[method].get('memory', 0) for method in methods]
            accuracy = [performance_data[method].get('accuracy', 0) for method in methods]
            
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
            
            # Execution time comparison
            ax1.bar(methods, times, color=plt.cm.viridis(np.linspace(0, 1, len(methods))))
            ax1.set_title('Execution Time Comparison', fontweight='bold')
            ax1.set_ylabel('Time (seconds)')
            ax1.tick_params(axis='x', rotation=45)
            
            # Memory usage comparison
            ax2.bar(methods, memory, color=plt.cm.plasma(np.linspace(0, 1, len(methods))))
            ax2.set_title('Memory Usage Comparison', fontweight='bold')
            ax2.set_ylabel('Memory (MB)')
            ax2.tick_params(axis='x', rotation=45)
            
            # Accuracy vs Time scatter plot
            ax3.scatter(times, accuracy, s=100, c=range(len(methods)), cmap='rainbow', alpha=0.7)
            ax3.set_xlabel('Execution Time (seconds)')
            ax3.set_ylabel('Accuracy Score')
            ax3.set_title('Accuracy vs Time Trade-off', fontweight='bold')
            
            # Add method labels to scatter plot
            for i, method in enumerate(methods):
                ax3.annotate(method, (times[i], accuracy[i]), xytext=(5, 5), 
                           textcoords='offset points', fontsize=8)
            
            # Performance radar chart
            categories = ['Speed', 'Memory Efficiency', 'Accuracy', 'Interpretability']
            fig_radar = plt.figure(figsize=(8, 8))
            ax_radar = fig_radar.add_subplot(111, projection='polar')
            
            # Normalize scores for radar chart
            max_time = max(times) if times else 1
            max_memory = max(memory) if memory else 1
            
            for i, method in enumerate(methods):
                scores = [
                    (1 - times[i]/max_time) * 100,  # Speed (inverse of time)
                    (1 - memory[i]/max_memory) * 100,  # Memory efficiency
                    accuracy[i] * 100,  # Accuracy
                    75  # Interpretability (fixed score for example)
                ]
                
                angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
                scores += scores[:1]  # Complete the circle
                angles += angles[:1]
                
                ax_radar.plot(angles, scores, 'o-', linewidth=2, label=method)
                ax_radar.fill(angles, scores, alpha=0.25)
            
            ax_radar.set_xticks(angles[:-1])
            ax_radar.set_xticklabels(categories)
            ax_radar.set_ylim(0, 100)
            ax_radar.set_title('Performance Comparison Radar Chart', fontweight='bold', pad=20)
            ax_radar.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
            
            plt.tight_layout()
            
            # Save to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150, facecolor='white')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error creating performance visualization: {e}")
            return ""
    
    def encode_image_to_base64(self, image: Image.Image) -> str:
        """Encode PIL Image to base64 string"""
        try:
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{image_str}"
        except Exception as e:
            print(f"Error encoding image to base64: {e}")
            return ""

# Performance optimization utilities
class PerformanceOptimizer:
    """Utilities for optimizing XAI method performance"""
    
    @staticmethod
    def optimize_shap_computation(model, input_tensor: torch.Tensor, 
                                background_samples: int = 50) -> Dict[str, Any]:
        """
        Optimize SHAP computation with sampling and caching
        
        Args:
            model: PyTorch model
            input_tensor: Input tensor
            background_samples: Number of background samples for SHAP
            
        Returns:
            Dictionary with optimization metrics
        """
        import time
        import psutil
        import os
        
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        try:
            # Use smaller background dataset for faster computation
            background_data = torch.randn(background_samples, *input_tensor.shape[1:])
            
            # Use optimized SHAP explainer
            explainer = shap.GradientExplainer(model, background_data)
            
            # Generate SHAP values with batching
            with torch.no_grad():
                shap_values = explainer.shap_values(input_tensor)
            
            end_time = time.time()
            end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
            
            return {
                'shap_values': shap_values,
                'computation_time': end_time - start_time,
                'memory_usage': end_memory - start_memory,
                'optimized': True,
                'background_samples': background_samples
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'computation_time': time.time() - start_time,
                'memory_usage': psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024 - start_memory,
                'optimized': False
            }
    
    @staticmethod
    def optimize_lime_computation(input_tensor: torch.Tensor, 
                                num_samples: int = 500) -> Dict[str, Any]:
        """
        Optimize LIME computation with reduced samples
        
        Args:
            input_tensor: Input tensor
            num_samples: Number of samples for LIME
            
        Returns:
            Dictionary with optimization metrics
        """
        import time
        import psutil
        import os
        
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        # Adaptive sampling based on image complexity
        image_variance = torch.var(input_tensor).item()
        if image_variance < 0.1:  # Low complexity image
            num_samples = min(num_samples, 200)
        elif image_variance > 0.5:  # High complexity image
            num_samples = min(num_samples, 800)
        
        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        return {
            'optimized_samples': num_samples,
            'image_variance': image_variance,
            'computation_time': end_time - start_time,
            'memory_usage': end_memory - start_memory,
            'optimized': True
        }
