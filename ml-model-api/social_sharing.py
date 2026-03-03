import os
import uuid
import base64
import io
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timezone

class SocialShareGenerator:
    def __init__(self, upload_folder: str = "uploads"):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)
        
        # Try to load a font, fallback to default
        try:
            self.title_font = ImageFont.truetype("arial.ttf", 48)
            self.subtitle_font = ImageFont.truetype("arial.ttf", 32)
            self.confidence_font = ImageFont.truetype("arial.ttf", 28)
        except:
            self.title_font = ImageFont.load_default()
            self.subtitle_font = ImageFont.load_default()
            self.confidence_font = ImageFont.load_default()
    
    def generate_shareable_image(self, original_image: Image.Image, 
                             prediction: str, 
                             confidence: float,
                             template: str = "default") -> str:
        """
        Generate a shareable image with prediction overlay
        
        Args:
            original_image: Original PIL Image
            prediction: Predicted food category
            confidence: Confidence score (0-1)
            template: Template style to use
            
        Returns:
            Base64 encoded image string
        """
        # Create a copy and resize for social media
        img = original_image.copy()
        img = img.resize((800, 600), Image.Resample.LANCZOS)
        
        # Create overlay
        overlay = Image.new('RGBA', (800, 600), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        if template == "default":
            self._draw_default_template(draw, prediction, confidence)
        elif template == "minimal":
            self._draw_minimal_template(draw, prediction, confidence)
        elif template == "colorful":
            self._draw_colorful_template(draw, prediction, confidence)
        
        # Composite overlay on image
        result = Image.alpha_composite(img.convert('RGBA'), overlay)
        
        # Convert to RGB for saving
        result = result.convert('RGB')
        
        # Save and encode to base64
        filename = f"share_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(self.upload_folder, filename)
        result.save(filepath, 'JPEG', quality=90)
        
        # Encode to base64
        with open(filepath, 'rb') as f:
            image_data = f.read()
        
        base64_str = base64.b64encode(image_data).decode()
        
        return f"data:image/jpeg;base64,{base64_str}"
    
    def _draw_default_template(self, draw: ImageDraw, prediction: str, confidence: float):
        """Draw default template overlay"""
        # Semi-transparent background for text
        draw.rectangle([50, 450, 750, 580], fill=(0, 0, 0, 180))
        
        # Title
        title_text = f"FlavorSnap AI"
        draw.text((70, 470), title_text, fill=(255, 255, 255), font=self.title_font)
        
        # Prediction
        pred_text = f"🍽 {prediction}"
        draw.text((70, 510), pred_text, fill=(255, 255, 255), font=self.subtitle_font)
        
        # Confidence
        conf_text = f"Confidence: {confidence:.1%}"
        draw.text((70, 545), conf_text, fill=(100, 255, 100), font=self.confidence_font)
    
    def _draw_minimal_template(self, draw: ImageDraw, prediction: str, confidence: float):
        """Draw minimal template overlay"""
        # Small bottom banner
        draw.rectangle([0, 550, 800, 600], fill=(0, 0, 0, 200))
        
        # Minimal text
        text = f"{prediction} • {confidence:.1%} confidence"
        draw.text((20, 565), text, fill=(255, 255, 255), font=self.subtitle_font)
    
    def _draw_colorful_template(self, draw: ImageDraw, prediction: str, confidence: float):
        """Draw colorful template overlay"""
        # Gradient background effect
        for i in range(100):
            alpha = int(255 * (1 - i/100))
            color = (255, 100 + i, 50 + i*2, alpha)
            draw.rectangle([50 + i, 400 + i, 750 - i, 500 - i], outline=color, width=2)
        
        # Center text box
        draw.rectangle([200, 420, 600, 480], fill=(255, 255, 255, 220))
        
        # Text
        draw.text((220, 435), prediction, fill=(0, 0, 0), font=self.title_font)
        draw.text((250, 465), f"{confidence:.1%}", fill=(0, 100, 0), font=self.confidence_font)
    
    def generate_share_text(self, prediction: str, confidence: float, 
                       platform: str = "twitter") -> str:
        """
        Generate shareable text for different platforms
        
        Args:
            prediction: Predicted food category
            confidence: Confidence score
            platform: Target social media platform
            
        Returns:
            Formatted share text
        """
        base_text = f"I just used FlavorSnap AI to identify {prediction}"
        
        if platform == "twitter":
            # Twitter has character limit
            if len(base_text) > 200:
                base_text = f"FlavorSnap AI identified: {prediction}"
            return f"{base_text} with {confidence:.1%} confidence! 🍽 #FlavorSnap #FoodAI #FoodRecognition"
        
        elif platform == "facebook":
            return f"{base_text} with {confidence:.1%} confidence! 🎉\n\nTry FlavorSnap AI yourself and see what delicious dishes you can identify! 📱\n\n#FlavorSnap #FoodAI #ArtificialIntelligence"
        
        elif platform == "instagram":
            return f"{base_text} ✨\n\nConfidence: {confidence:.1%}\n\n🤖 AI: @FlavorSnap\n#FlavorSnap #FoodAI #Tech #FoodPhotography"
        
        elif platform == "linkedin":
            return f"I'm excited to share my experience with FlavorSnap AI, an innovative food recognition system. The AI successfully identified {prediction} with {confidence:.1%} confidence.\n\nThis demonstrates the impressive capabilities of modern computer vision in food recognition and culinary applications.\n\n#AI #FoodTech #ComputerVision #Innovation #FlavorSnap"
        
        else:
            return f"{base_text} with {confidence:.1%} confidence! #FlavorSnap #FoodAI"
    
    def generate_open_graph_metadata(self, prediction: str, confidence: float, 
                                image_url: str) -> Dict[str, str]:
        """
        Generate OpenGraph metadata for social sharing
        
        Args:
            prediction: Predicted food category
            confidence: Confidence score
            image_url: URL to the shareable image
            
        Returns:
            Dictionary with OpenGraph metadata
        """
        return {
            "og:title": f"FlavorSnap AI: {prediction}",
            "og:description": f"I used FlavorSnap AI to identify {prediction} with {confidence:.1%} confidence! Try it yourself!",
            "og:image": image_url,
            "og:image:alt": f"AI food recognition result: {prediction}",
            "og:type": "website",
            "og:site_name": "FlavorSnap",
            "og:url": "https://flavorsnap.com",
            "twitter:card": "summary_large_image",
            "twitter:title": f"FlavorSnap AI: {prediction}",
            "twitter:description": f"Identified {prediction} with {confidence:.1%} confidence using AI! 🍽",
            "twitter:image": image_url,
            "twitter:site": "@FlavorSnapAI"
        }
    
    def create_shareable_response(self, original_image: Image.Image,
                              prediction: str,
                              confidence: float,
                              platforms: List[str] = None) -> Dict[str, Any]:
        """
        Create complete shareable response with all platforms
        
        Args:
            original_image: Original PIL Image
            prediction: Predicted food category
            confidence: Confidence score
            platforms: List of platforms to generate content for
            
        Returns:
            Dictionary with all shareable content
        """
        if platforms is None:
            platforms = ["twitter", "facebook", "instagram", "linkedin"]
        
        # Generate shareable image
        shareable_image = self.generate_shareable_image(original_image, prediction, confidence)
        
        # Generate share text for each platform
        share_texts = {}
        for platform in platforms:
            share_texts[platform] = self.generate_share_text(prediction, confidence, platform)
        
        # Generate OpenGraph metadata
        og_metadata = self.generate_open_graph_metadata(prediction, confidence, shareable_image)
        
        # Generate share URLs
        share_urls = {}
        base_url = "https://flavorsnap.com"
        
        for platform in platforms:
            if platform == "twitter":
                text = share_texts[platform]
                encoded_text = text.replace(" ", "%20").replace("#", "%23")
                share_urls[platform] = f"https://twitter.com/intent/tweet?text={encoded_text}"
            elif platform == "facebook":
                share_urls[platform] = f"https://www.facebook.com/sharer/sharer.php?u={base_url}"
            elif platform == "linkedin":
                share_urls[platform] = f"https://www.linkedin.com/sharing/share-offsite/?url={base_url}"
            elif platform == "instagram":
                share_urls[platform] = "https://www.instagram.com/"  # Instagram doesn't support direct sharing
            else:
                share_urls[platform] = f"{base_url}?share={platform}"
        
        return {
            "success": True,
            "shareable_image": shareable_image,
            "share_texts": share_texts,
            "share_urls": share_urls,
            "open_graph_metadata": og_metadata,
            "prediction": prediction,
            "confidence": confidence,
            "platforms": platforms
        }
    
    def track_sharing_analytics(self, prediction: str, platform: str, 
                             user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Track sharing analytics (placeholder for actual analytics implementation)
        
        Args:
            prediction: Predicted food category
            platform: Social media platform
            user_id: Optional user identifier
            
        Returns:
            Analytics tracking response
        """
        # This would integrate with your analytics system
        analytics_data = {
            "event": "social_share",
            "prediction": prediction,
            "platform": platform,
            "user_id": user_id or "anonymous",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_agent": "FlavorSnap Web App"
        }
        
        # Log analytics (in production, this would go to your analytics service)
        print(f"Analytics Event: {json.dumps(analytics_data)}")
        
        return {
            "success": True,
            "tracked": True,
            "analytics_id": str(uuid.uuid4()),
            "message": "Sharing event tracked successfully"
        }
