import torch
import torch.nn.functional as F
import numpy as np
import cv2
from PIL import Image
import torchvision.transforms as transforms
from torchvision import models
from typing import Dict, List, Tuple, Any, Optional
import json
import base64
import io
import shap
import lime
import lime.lime_image
from lime.wrappers.scikit_image import SegmentationAlgorithm
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from skimage.segmentation import mark_boundaries
import warnings
warnings.filterwarnings('ignore')

class ModelExplainer:
    def __init__(self, model, target_layers: List[str] = None):
        """
        Initialize the model explainer with comprehensive XAI capabilities
        
        Args:
            model: The PyTorch model to explain
            target_layers: List of layer names to use for Grad-CAM
        """
        self.model = model
        self.model.eval()
        
        # Default target layers for ResNet18
        if target_layers is None:
            self.target_layers = ['layer4']
        else:
            self.target_layers = target_layers
            
        # Hook storage
        self.gradients = {}
        self.activations = {}
        
        # Initialize SHAP explainer
        self.shap_explainer = None
        
        # Initialize LIME explainer
        self.lime_explainer = None
        
        # Register hooks
        self._register_hooks()
        
        # Initialize explainers
        self._initialize_explainers()
    
    def _initialize_explainers(self):
        """Initialize SHAP and LIME explainers"""
        try:
            # Initialize SHAP explainer (using GradientExplainer for PyTorch models)
            # Create a dummy input for initialization
            dummy_input = torch.zeros((1, 3, 224, 224))
            if hasattr(self.model, 'cpu'):
                model_cpu = self.model.cpu()
            else:
                model_cpu = self.model
            
            self.shap_explainer = shap.GradientExplainer(model_cpu, dummy_input)
            
            # Initialize LIME explainer
            self.lime_explainer = lime.lime_image.LimeImageExplainer()
            
        except Exception as e:
            print(f"Warning: Could not initialize explainers: {e}")
            self.shap_explainer = None
            self.lime_explainer = None
    
    def _register_hooks(self):
        """Register forward and backward hooks to capture activations and gradients"""
        
        def get_activation(name):
            def hook(module, input, output):
                self.activations[name] = output.detach()
            return hook
        
        def get_gradient(name):
            def hook(module, grad_input, grad_output):
                self.gradients[name] = grad_output[0].detach()
            return hook
        
        # Find and register hooks for target layers
        for name, module in self.model.named_modules():
            if any(target in name for target in self.target_layers):
                module.register_forward_hook(get_activation(name))
                module.register_backward_hook(get_gradient(name))
    
    def generate_grad_cam(self, input_tensor: torch.Tensor, class_idx: int) -> np.ndarray:
        """
        Generate Grad-CAM heatmap for a specific class
        
        Args:
            input_tensor: Input tensor of shape (1, C, H, W)
            class_idx: Target class index
            
        Returns:
            numpy array representing the heatmap
        """
        # Forward pass
        output = self.model(input_tensor)
        
        # Zero gradients
        self.model.zero_grad()
        
        # Backward pass for target class
        class_score = output[0, class_idx]
        class_score.backward()
        
        # Get gradients and activations
        gradients = None
        activations = None
        
        for layer_name in self.target_layers:
            if layer_name in self.gradients and layer_name in self.activations:
                gradients = self.gradients[layer_name]
                activations = self.activations[layer_name]
                break
        
        if gradients is None or activations is None:
            # Fallback: create a uniform heatmap
            return np.ones((224, 224), dtype=np.float32) * 0.5
        
        # Global average pooling of gradients
        weights = torch.mean(gradients, dim=(2, 3), keepdim=True)
        
        # Weighted combination of activation maps
        cam = torch.sum(weights * activations, dim=1)
        cam = F.relu(cam)
        
        # Normalize to [0, 1]
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-8)
        
        # Convert to numpy and resize
        cam = cam.squeeze().cpu().numpy()
        cam = cv2.resize(cam, (input_tensor.shape[2], input_tensor.shape[3]))
        
        return cam
    
    def generate_feature_importance(self, input_tensor: torch.Tensor, top_k: int = 10) -> Dict[str, float]:
        """
        Generate feature importance scores using integrated gradients
        
        Args:
            input_tensor: Input tensor
            top_k: Number of top features to return
            
        Returns:
            Dictionary mapping feature indices to importance scores
        """
        # Set model to evaluation mode
        self.model.eval()
        
        # Get baseline (black image)
        baseline = torch.zeros_like(input_tensor)
        
        # Integrated gradients
        n_steps = 50
        integrated_gradients = torch.zeros_like(input_tensor)
        
        for step in range(n_steps + 1):
            alpha = step / n_steps
            interpolated_input = baseline + alpha * (input_tensor - baseline)
            interpolated_input.requires_grad_(True)
            
            output = self.model(interpolated_input)
            class_idx = output.argmax(dim=1).item()
            class_score = output[0, class_idx]
            
            if step > 0:
                self.model.zero_grad()
                class_score.backward(retain_graph=True)
                integrated_gradients += interpolated_input.grad / n_steps
        
        # Calculate importance scores
        importance_scores = torch.abs(integrated_gradients).mean(dim=(2, 3)).squeeze()
        
        # Get top-k features
        top_indices = torch.topk(importance_scores, min(top_k, len(importance_scores))).indices
        
        feature_importance = {}
        for idx in top_indices:
            feature_importance[f"feature_{idx.item()}"] = importance_scores[idx].item()
        
        return feature_importance
    
    def generate_shap_values(self, input_tensor: torch.Tensor, class_idx: int = None) -> Dict[str, Any]:
        """
        Generate SHAP values for model explanation
        
        Args:
            input_tensor: Input tensor of shape (1, C, H, W)
            class_idx: Target class index (if None, uses predicted class)
            
        Returns:
            Dictionary containing SHAP values and visualizations
        """
        if self.shap_explainer is None:
            return {"error": "SHAP explainer not initialized"}
        
        try:
            # Ensure model is on CPU for SHAP
            model_device = next(self.model.parameters()).device
            if model_device != torch.device('cpu'):
                self.model.cpu()
            
            # Get model prediction
            with torch.no_grad():
                output = self.model(input_tensor)
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
                
            if class_idx is None:
                class_idx = torch.argmax(probabilities).item()
            
            # Generate SHAP values
            shap_values = self.shap_explainer.shap_values(input_tensor, ranked_outputs=1)
            
            # Handle different SHAP output formats
            if isinstance(shap_values, list):
                shap_values = shap_values[0] if len(shap_values) > 0 else shap_values
            
            # Convert to numpy and process
            if isinstance(shap_values, torch.Tensor):
                shap_values = shap_values.detach().cpu().numpy()
            
            # Create SHAP visualization
            shap_image = self._create_shap_visualization(input_tensor, shap_values, class_idx)
            
            # Calculate feature importance from SHAP values
            shap_importance = self._calculate_shap_importance(shap_values)
            
            # Restore model device
            self.model.to(model_device)
            
            return {
                "shap_values": shap_values.tolist() if hasattr(shap_values, 'tolist') else str(shap_values),
                "shap_image": shap_image,
                "feature_importance": shap_importance,
                "class_idx": class_idx,
                "explanation": f"SHAP values show how each pixel/region contributed to the classification of class {class_idx}"
            }
            
        except Exception as e:
            return {"error": f"Failed to generate SHAP values: {str(e)}"}
    
    def _create_shap_visualization(self, input_tensor: torch.Tensor, shap_values: np.ndarray, class_idx: int) -> str:
        """Create SHAP visualization and return as base64 string"""
        try:
            # Convert input tensor to numpy
            input_np = input_tensor.squeeze().permute(1, 2, 0).cpu().numpy()
            
            # Denormalize the image
            mean = np.array([0.485, 0.456, 0.406])
            std = np.array([0.229, 0.224, 0.225])
            input_np = input_np * std + mean
            input_np = np.clip(input_np, 0, 1)
            
            # Create visualization
            plt.figure(figsize=(12, 4))
            
            # Original image
            plt.subplot(1, 3, 1)
            plt.imshow(input_np)
            plt.title('Original Image')
            plt.axis('off')
            
            # SHAP values
            if len(shap_values.shape) == 3:
                shap_plot = shap_values.transpose(1, 2, 0)
                # Take absolute values for visualization
                shap_abs = np.abs(shap_plot)
                if shap_abs.shape[2] > 3:
                    shap_abs = shap_abs[:, :, :3]
                shap_abs = shap_abs / (shap_abs.max() + 1e-8)
                
                plt.subplot(1, 3, 2)
                plt.imshow(shap_abs)
                plt.title('SHAP Values (Absolute)')
                plt.axis('off')
                
                # Combined visualization
                plt.subplot(1, 3, 3)
                plt.imshow(input_np)
                plt.imshow(shap_abs, alpha=0.5, cmap='jet')
                plt.title('SHAP Overlay')
                plt.axis('off')
            
            plt.tight_layout()
            
            # Save to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error creating SHAP visualization: {e}")
            return ""
    
    def _calculate_shap_importance(self, shap_values: np.ndarray) -> Dict[str, float]:
        """Calculate feature importance from SHAP values"""
        try:
            if len(shap_values.shape) == 3:
                # Average absolute SHAP values across spatial dimensions
                importance = np.mean(np.abs(shap_values), axis=(1, 2))
            else:
                importance = np.abs(shap_values.flatten())
            
            # Get top features
            top_k = min(10, len(importance))
            top_indices = np.argsort(importance)[::-1][:top_k]
            
            feature_importance = {}
            for i, idx in enumerate(top_indices):
                feature_importance[f"feature_{idx}"] = float(importance[idx])
            
            return feature_importance
            
        except Exception as e:
            print(f"Error calculating SHAP importance: {e}")
            return {}
    
    def generate_lime_explanation(self, input_tensor: torch.Tensor, class_idx: int = None, 
                                 num_samples: int = 1000) -> Dict[str, Any]:
        """
        Generate LIME explanation for model prediction
        
        Args:
            input_tensor: Input tensor of shape (1, C, H, W)
            class_idx: Target class index (if None, uses predicted class)
            num_samples: Number of samples for LIME explanation
            
        Returns:
            Dictionary containing LIME explanation and visualization
        """
        if self.lime_explainer is None:
            return {"error": "LIME explainer not initialized"}
        
        try:
            # Convert tensor to numpy image
            input_np = input_tensor.squeeze().permute(1, 2, 0).cpu().numpy()
            
            # Denormalize the image
            mean = np.array([0.485, 0.456, 0.406])
            std = np.array([0.229, 0.224, 0.225])
            input_np = input_np * std + mean
            input_np = np.clip(input_np, 0, 1)
            
            # Get model prediction
            with torch.no_grad():
                output = self.model(input_tensor)
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
                
            if class_idx is None:
                class_idx = torch.argmax(probabilities).item()
            
            # Create prediction function for LIME
            def predict_fn(images):
                """Prediction function for LIME"""
                batch = []
                for img in images:
                    # Normalize image
                    img_normalized = (img - mean) / std
                    img_tensor = torch.from_numpy(img_normalized).permute(2, 0, 1).float()
                    batch.append(img_tensor)
                
                batch_tensor = torch.stack(batch)
                
                with torch.no_grad():
                    outputs = self.model(batch_tensor)
                    probs = torch.nn.functional.softmax(outputs, dim=1)
                    
                return probs.cpu().numpy()
            
            # Generate LIME explanation
            explanation = self.lime_explainer.explain_instance(
                input_np,
                predict_fn,
                top_labels=5,
                hide_color=0,
                num_samples=num_samples,
                segmentation_fn=SegmentationAlgorithm('quickshift', kernel_size=4, max_dist=200, ratio=0.2)
            )
            
            # Get explanation for target class
            temp, mask = explanation.get_image_and_mask(
                class_idx,
                positive_only=True,
                num_features=10,
                hide_rest=False
            )
            
            # Create LIME visualization
            lime_image = self._create_lime_visualization(input_np, temp, mask, explanation)
            
            # Get feature importance
            feature_importance = self._extract_lime_importance(explanation, class_idx)
            
            return {
                "lime_image": lime_image,
                "feature_importance": feature_importance,
                "class_idx": class_idx,
                "segments": mask.tolist() if hasattr(mask, 'tolist') else str(mask),
                "explanation": f"LIME highlights regions that were most important for classifying as class {class_idx}"
            }
            
        except Exception as e:
            return {"error": f"Failed to generate LIME explanation: {str(e)}"}
    
    def _create_lime_visualization(self, original_image: np.ndarray, temp: np.ndarray, 
                                  mask: np.ndarray, explanation) -> str:
        """Create LIME visualization and return as base64 string"""
        try:
            plt.figure(figsize=(15, 5))
            
            # Original image
            plt.subplot(1, 3, 1)
            plt.imshow(original_image)
            plt.title('Original Image')
            plt.axis('off')
            
            # LIME explanation
            plt.subplot(1, 3, 2)
            plt.imshow(mark_boundaries(temp, mask))
            plt.title('LIME Explanation')
            plt.axis('off')
            
            # Combined with boundaries
            plt.subplot(1, 3, 3)
            plt.imshow(original_image)
            plt.imshow(mark_boundaries(temp, mask), alpha=0.5)
            plt.title('LIME Overlay')
            plt.axis('off')
            
            plt.tight_layout()
            
            # Save to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error creating LIME visualization: {e}")
            return ""
    
    def _extract_lime_importance(self, explanation, class_idx: int) -> Dict[str, float]:
        """Extract feature importance from LIME explanation"""
        try:
            # Get explanation for the specific class
            local_exp = explanation.local_exp[class_idx]
            
            feature_importance = {}
            for feature_id, importance in local_exp:
                feature_importance[f"segment_{feature_id}"] = float(importance)
            
            return feature_importance
            
        except Exception as e:
            print(f"Error extracting LIME importance: {e}")
            return {}
    
    def generate_confidence_explanation(self, probabilities: torch.Tensor, class_names: List[str]) -> Dict[str, Any]:
        """
        Generate confidence explanation for model predictions
        
        Args:
            probabilities: Model output probabilities
            class_names: List of class names
            
        Returns:
            Dictionary containing confidence explanations
        """
        probs = probabilities.squeeze().cpu().numpy()
        
        # Get top predictions
        top_k = min(5, len(probs))
        top_indices = np.argsort(probs)[::-1][:top_k]
        
        explanations = []
        for i, idx in enumerate(top_indices):
            confidence = probs[idx]
            class_name = class_names[idx] if idx < len(class_names) else f"Class_{idx}"
            
            explanation = {
                "rank": i + 1,
                "class": class_name,
                "confidence": float(confidence),
                "percentage": float(confidence * 100),
                "certainty_level": self._get_certainty_level(confidence),
                "explanation": self._generate_confidence_text(confidence, i)
            }
            explanations.append(explanation)
        
        # Overall confidence metrics
        entropy = -np.sum(probs * np.log(probs + 1e-8))
        max_confidence = np.max(probs)
        
        return {
            "predictions": explanations,
            "overall_confidence": float(max_confidence),
            "entropy": float(entropy),
            "certainty": "high" if max_confidence > 0.8 else "medium" if max_confidence > 0.5 else "low",
            "is_confident": max_confidence > 0.7
        }
    
    def _get_certainty_level(self, confidence: float) -> str:
        """Get certainty level based on confidence score"""
        if confidence > 0.9:
            return "Very High"
        elif confidence > 0.7:
            return "High"
        elif confidence > 0.5:
            return "Medium"
        elif confidence > 0.3:
            return "Low"
        else:
            return "Very Low"
    
    def _generate_confidence_text(self, confidence: float, rank: int) -> str:
        """Generate explanatory text for confidence level"""
        if rank == 0:  # Top prediction
            if confidence > 0.9:
                return "Extremely confident - this is very likely the correct classification"
            elif confidence > 0.7:
                return "Highly confident - strong evidence for this classification"
            elif confidence > 0.5:
                return "Moderately confident - some uncertainty but likely correct"
            else:
                return "Low confidence - classification is uncertain"
        else:
            return f"Alternative prediction with {confidence:.1%} confidence"
    
    def find_similar_images(self, input_features: torch.Tensor, 
                          image_database: List[np.ndarray] = None, 
                          top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Find similar images based on feature similarity
        
        Args:
            input_features: Feature representation of input image
            image_database: Database of image features to compare against
            top_k: Number of similar images to return
            
        Returns:
            List of similar image information
        """
        if image_database is None:
            # Return placeholder similar images
            return [
                {
                    "similarity_score": 0.85,
                    "image_path": "placeholder_similar_1.jpg",
                    "predicted_class": "Similar Dish 1",
                    "explanation": "Very similar in appearance and likely the same category"
                },
                {
                    "similarity_score": 0.72,
                    "image_path": "placeholder_similar_2.jpg", 
                    "predicted_class": "Similar Dish 2",
                    "explanation": "Similar cooking style and ingredients"
                },
                {
                    "similarity_score": 0.68,
                    "image_path": "placeholder_similar_3.jpg",
                    "predicted_class": "Similar Dish 3", 
                    "explanation": "Similar presentation and texture"
                }
            ]
        
        # Calculate cosine similarity with database images
        similarities = []
        input_norm = F.normalize(input_features.flatten(), p=2, dim=0)
        
        for i, db_features in enumerate(image_database):
            db_norm = F.normalize(torch.from_numpy(db_features).flatten(), p=2, dim=0)
            similarity = torch.dot(input_norm, db_norm).item()
            similarities.append((i, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k similar images
        similar_images = []
        for i, (idx, similarity) in enumerate(similarities[:top_k]):
            similar_images.append({
                "similarity_score": float(similarity),
                "image_path": f"similar_image_{idx}.jpg",
                "predicted_class": f"Similar Class {idx}",
                "explanation": f"Similarity score: {similarity:.2f}"
            })
        
        return similar_images
    
    def generate_educational_tooltip(self, class_name: str, confidence: float) -> Dict[str, str]:
        """
        Generate educational tooltips for predictions
        
        Args:
            class_name: Predicted class name
            confidence: Confidence score
            
        Returns:
            Dictionary containing educational information
        """
        tooltips = {
            "general": f"The model is {confidence:.1%} confident that this is {class_name}.",
            "confidence": f"Confidence scores indicate how certain the model is about its prediction.",
            "features": "The model analyzes visual features like color, texture, shape, and composition.",
            "learning": f"The model learned to identify {class_name} from many example images during training.",
            "improvement": "Higher confidence typically comes from clear, well-lit images with distinctive features."
        }
        
        # Add class-specific information
        class_specific = self._get_class_specific_info(class_name)
        tooltips.update(class_specific)
        
        return tooltips
    
    def _get_class_specific_info(self, class_name: str) -> Dict[str, str]:
        """Get class-specific educational information"""
        # This would be expanded with actual food knowledge
        class_info = {
            "Jollof Rice": {
                "origin": "Jollof rice is a popular West African dish known for its vibrant red color and aromatic spices.",
                "features": "Key visual features include reddish-orange color, rice grains, and often served with protein.",
                "variations": "Regional variations exist across West Africa, with different spice blends and cooking methods."
            },
            "Egusi Soup": {
                "origin": "Egusi soup is a Nigerian dish made from melon seeds.",
                "features": "Typically has a thick, chunky texture with greenish-brown color.",
                "ingredients": "Contains ground melon seeds, leafy vegetables, and various proteins."
            }
        }
        
        return class_info.get(class_name, {
            "origin": f"{class_name} is a traditional dish that the model has learned to recognize.",
            "features": "The model identifies this dish based on its characteristic appearance and presentation.",
            "variations": "There may be regional variations in preparation and presentation."
        })
    
    def create_explanation_overlay(self, original_image: Image.Image, 
                               heatmap: np.ndarray, 
                               confidence: float) -> Image.Image:
        """
        Create an overlay image with heatmap and confidence information
        
        Args:
            original_image: Original PIL Image
            heatmap: Grad-CAM heatmap
            confidence: Confidence score
            
        Returns:
            PIL Image with overlay
        """
        # Convert original image to numpy
        original_np = np.array(original_image.resize((224, 224)))
        
        # Create colormap for heatmap
        heatmap_colored = cv2.applyColorMap(np.uint8(255 * heatmap), cv2.COLORMAP_JET)
        
        # Overlay heatmap on original image
        overlay = cv2.addWeighted(original_np, 0.6, heatmap_colored, 0.4, 0)
        
        # Convert back to PIL
        overlay_image = Image.fromarray(overlay)
        
        return overlay_image
    
    def encode_image_to_base64(self, image: Image.Image) -> str:
        """Encode PIL Image to base64 string"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_str = base64.b64encode(buffer.getvalue()).decode()
        return image_str
