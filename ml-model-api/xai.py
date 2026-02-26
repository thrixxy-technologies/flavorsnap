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

class ModelExplainer:
    def __init__(self, model, target_layers: List[str] = None):
        """
        Initialize the model explainer with Grad-CAM capability
        
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
        
        # Register hooks
        self._register_hooks()
    
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
