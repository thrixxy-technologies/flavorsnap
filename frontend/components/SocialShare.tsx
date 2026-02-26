import React, { useState } from 'react';
import { useTranslation } from 'next-i18next';

interface SocialShareProps {
  prediction: string;
  confidence: number;
  imageUrl?: string;
  onShare?: (platform: string, data: any) => void;
}

const SocialShare: React.FC<SocialShareProps> = ({ 
  prediction, 
  confidence, 
  imageUrl, 
  onShare 
}) => {
  const { t } = useTranslation('common');
  const [showShareMenu, setShowShareMenu] = useState(false);
  const [shareableImage, setShareableImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState('default');

  const platforms = [
    { 
      id: 'twitter', 
      name: 'Twitter', 
      icon: '🐦', 
      color: 'bg-blue-400 hover:bg-blue-500' 
    },
    { 
      id: 'facebook', 
      name: 'Facebook', 
      icon: '📘', 
      color: 'bg-blue-600 hover:bg-blue-700' 
    },
    { 
      id: 'instagram', 
      name: 'Instagram', 
      icon: '📷', 
      color: 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600' 
    },
    { 
      id: 'linkedin', 
      name: 'LinkedIn', 
      icon: '💼', 
      color: 'bg-blue-700 hover:bg-blue-800' 
    }
  ];

  const templates = [
    { id: 'default', name: 'Default', preview: '🎨' },
    { id: 'minimal', name: 'Minimal', preview: '⚪' },
    { id: 'colorful', name: 'Colorful', preview: '🌈' }
  ];

  const generateShareableContent = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/social/generate-shareable', {
        method: 'POST',
        body: JSON.stringify({
          prediction,
          confidence,
          platforms: platforms.map(p => p.id),
          template: selectedTemplate
        }),
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to generate shareable content');
      }

      const data = await response.json();
      setShareableImage(data.data.shareable_image);
      
      if (onShare) {
        onShare('generated', data.data);
      }
    } catch (error) {
      console.error('Error generating shareable content:', error);
    } finally {
      setLoading(false);
    }
  };

  const shareToPlatform = async (platform: string) => {
    try {
      const response = await fetch('/api/social/track-share', {
        method: 'POST',
        body: JSON.stringify({
          prediction,
          platform,
          user_id: localStorage.getItem('userId') || 'anonymous'
        }),
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const shareData = await response.json();
      
      if (onShare) {
        onShare(platform, shareData);
      }

      // Get share URL for the platform
      const shareUrls = {
        twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(
          `I just used FlavorSnap AI to identify ${prediction} with ${(confidence * 100).toFixed(1)}% confidence! 🍽 #FlavorSnap #FoodAI`
        )}`,
        facebook: 'https://www.facebook.com/sharer/sharer.php?u=https://flavorsnap.com',
        linkedin: 'https://www.linkedin.com/sharing/share-offsite/?url=https://flavorsnap.com',
        instagram: 'https://www.instagram.com/' // Instagram doesn't support direct sharing
      };

      const shareUrl = shareUrls[platform as keyof typeof shareUrls];
      if (shareUrl) {
        window.open(shareUrl, '_blank', 'width=600,height=400');
      }
    } catch (error) {
      console.error('Error sharing to platform:', error);
    }
  };

  const downloadShareableImage = () => {
    if (shareableImage) {
      const link = document.createElement('a');
      link.href = shareableImage;
      link.download = `flavorsnap-${prediction.toLowerCase().replace(/\s+/g, '-')}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const copyShareText = async (platform: string) => {
    try {
      const response = await fetch('/api/social/share-text', {
        method: 'POST',
        body: JSON.stringify({
          prediction,
          confidence,
          platform
        }),
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();
      
      await navigator.clipboard.writeText(data.share_text);
      
      // Show success feedback
      const button = document.getElementById(`copy-${platform}`);
      if (button) {
        const originalText = button.textContent || '';
        button.textContent = t('copied');
        setTimeout(() => {
          button.textContent = originalText;
        }, 2000);
      }
    } catch (error) {
      console.error('Error copying share text:', error);
    }
  };

  return (
    <div className="max-w-md mx-auto p-4 bg-white rounded-lg shadow-lg">
      <h3 className="text-lg font-semibold mb-4 text-gray-800">
        {t('share_your_discovery')}
      </h3>

      {/* Shareable Image Preview */}
      {shareableImage && (
        <div className="mb-6">
          <img 
            src={shareableImage} 
            alt="Shareable result"
            className="w-full rounded-lg border border-gray-200"
          />
        </div>
      )}

      {/* Template Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {t('choose_template')}
        </label>
        <div className="flex space-x-2">
          {templates.map((template) => (
            <button
              key={template.id}
              onClick={() => setSelectedTemplate(template.id)}
              className={`px-3 py-2 rounded-md border-2 transition-colors ${
                selectedTemplate === template.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <span className="mr-2">{template.preview}</span>
              {template.name}
            </button>
          ))}
        </div>
      </div>

      {/* Generate Button */}
      {!shareableImage && (
        <button
          onClick={generateShareableContent}
          disabled={loading}
          className="w-full mb-6 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? t('generating') : t('generate_shareable_image')}
        </button>
      )}

      {/* Platform Sharing */}
      {shareableImage && (
        <div className="space-y-4">
          <h4 className="text-md font-medium text-gray-700 mb-3">
            {t('share_to_platforms')}
          </h4>
          
          <div className="grid grid-cols-2 gap-3">
            {platforms.map((platform) => (
              <div key={platform.id} className="space-y-2">
                <button
                  onClick={() => shareToPlatform(platform.id)}
                  className={`w-full ${platform.color} text-white px-3 py-2 rounded-md transition-colors`}
                >
                  <span className="mr-2">{platform.icon}</span>
                  {platform.name}
                </button>
                
                <button
                  id={`copy-${platform.id}`}
                  onClick={() => copyShareText(platform.id)}
                  className="w-full bg-gray-100 text-gray-700 px-3 py-1 rounded text-sm hover:bg-gray-200 transition-colors"
                >
                  {t('copy_text')}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Download Button */}
      {shareableImage && (
        <button
          onClick={downloadShareableImage}
          className="w-full mt-4 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors"
        >
          {t('download_image')}
        </button>
      )}

      {/* Share Stats */}
      <div className="mt-6 p-4 bg-gray-50 rounded-md">
        <h4 className="text-sm font-medium text-gray-700 mb-2">
          {t('share_stats')}
        </h4>
        <div className="text-xs text-gray-600 space-y-1">
          <p>🍽 {t('prediction')}: {prediction}</p>
          <p>📊 {t('confidence')}: {(confidence * 100).toFixed(1)}%</p>
          <p>🎨 {t('template')}: {selectedTemplate}</p>
        </div>
      </div>
    </div>
  );
};

export default SocialShare;
