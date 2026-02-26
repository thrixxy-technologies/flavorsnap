import React, { useState, useRef } from 'react';
import { useTranslation } from 'next-i18next';

interface CategorySubmissionProps {
  onSubmit: (data: CategorySubmissionData) => void;
  loading?: boolean;
}

export interface CategorySubmissionData {
  name: string;
  description: string;
  submitted_by: string;
  images: File[];
}

const CategorySubmission: React.FC<CategorySubmissionProps> = ({ onSubmit, loading = false }) => {
  const { t } = useTranslation('common');
  const [formData, setFormData] = useState<CategorySubmissionData>({
    name: '',
    description: '',
    submitted_by: '',
    images: []
  });
  const [previewImages, setPreviewImages] = useState<string[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    
    // Validate file types and sizes
    const validFiles = files.filter(file => {
      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        setErrors(prev => ({ 
          ...prev, 
          images: `${file.name} is not a valid image type. Please use JPG, PNG, GIF, or WebP.` 
        }));
        return false;
      }
      
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        setErrors(prev => ({ 
          ...prev, 
          images: `${file.name} is too large. Please use images smaller than 5MB.` 
        }));
        return false;
      }
      
      return true;
    });

    const newImages = [...formData.images, ...validFiles];
    setFormData(prev => ({ ...prev, images: newImages }));

    // Create preview URLs
    const newPreviews = validFiles.map(file => URL.createObjectURL(file));
    setPreviewImages(prev => [...prev, ...newPreviews]);

    // Clear image errors
    if (errors.images) {
      setErrors(prev => ({ ...prev, images: '' }));
    }
  };

  const removeImage = (index: number) => {
    const newImages = formData.images.filter((_, i) => i !== index);
    const newPreviews = previewImages.filter((_, i) => i !== index);
    
    // Revoke the URL to avoid memory leaks
    URL.revokeObjectURL(previewImages[index]);
    
    setFormData(prev => ({ ...prev, images: newImages }));
    setPreviewImages(newPreviews);
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Food category name is required';
    } else if (formData.name.length < 3) {
      newErrors.name = 'Name must be at least 3 characters long';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    } else if (formData.description.length < 10) {
      newErrors.description = 'Description must be at least 10 characters long';
    }

    if (!formData.submitted_by.trim()) {
      newErrors.submitted_by = 'Your name is required';
    }

    if (formData.images.length === 0) {
      newErrors.images = 'At least one image is required';
    } else if (formData.images.length > 10) {
      newErrors.images = 'Maximum 10 images allowed';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (validateForm()) {
      onSubmit(formData);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      submitted_by: '',
      images: []
    });
    
    // Clean up preview URLs
    previewImages.forEach(url => URL.revokeObjectURL(url));
    setPreviewImages([]);
    setErrors({});
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">
        {t('submit_new_category')}
      </h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Name Field */}
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
            {t('category_name')} *
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.name ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder={t('enter_category_name')}
            disabled={loading}
          />
          {errors.name && (
            <p className="mt-1 text-sm text-red-600">{errors.name}</p>
          )}
        </div>

        {/* Description Field */}
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
            {t('description')} *
          </label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            rows={4}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.description ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder={t('describe_food_category')}
            disabled={loading}
          />
          {errors.description && (
            <p className="mt-1 text-sm text-red-600">{errors.description}</p>
          )}
        </div>

        {/* Submitted By Field */}
        <div>
          <label htmlFor="submitted_by" className="block text-sm font-medium text-gray-700 mb-2">
            {t('your_name')} *
          </label>
          <input
            type="text"
            id="submitted_by"
            name="submitted_by"
            value={formData.submitted_by}
            onChange={handleInputChange}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.submitted_by ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder={t('enter_your_name')}
            disabled={loading}
          />
          {errors.submitted_by && (
            <p className="mt-1 text-sm text-red-600">{errors.submitted_by}</p>
          )}
        </div>

        {/* Image Upload */}
        <div>
          <label htmlFor="images" className="block text-sm font-medium text-gray-700 mb-2">
            {t('upload_images')} * ({formData.images.length}/10)
          </label>
          <input
            ref={fileInputRef}
            type="file"
            id="images"
            name="images"
            multiple
            accept="image/*"
            onChange={handleImageSelect}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.images ? 'border-red-500' : 'border-gray-300'
            }`}
            disabled={loading || formData.images.length >= 10}
          />
          <p className="mt-1 text-sm text-gray-500">
            {t('image_requirements')}: JPG, PNG, GIF, WebP (max 5MB each)
          </p>
          {errors.images && (
            <p className="mt-1 text-sm text-red-600">{errors.images}</p>
          )}
        </div>

        {/* Image Preview */}
        {previewImages.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              {t('image_preview')}
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {previewImages.map((preview, index) => (
                <div key={index} className="relative group">
                  <img
                    src={preview}
                    alt={`Preview ${index + 1}`}
                    className="w-full h-32 object-cover rounded-md border border-gray-300"
                  />
                  <button
                    type="button"
                    onClick={() => removeImage(index)}
                    className="absolute top-2 right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    disabled={loading}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Form Actions */}
        <div className="flex gap-4">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? t('submitting') : t('submit_for_review')}
          </button>
          <button
            type="button"
            onClick={resetForm}
            disabled={loading}
            className="flex-1 bg-gray-200 text-gray-800 py-2 px-4 rounded-md hover:bg-gray-300 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
          >
            {t('reset_form')}
          </button>
        </div>
      </form>

      {/* Submission Guidelines */}
      <div className="mt-6 p-4 bg-blue-50 rounded-md">
        <h3 className="text-sm font-medium text-blue-800 mb-2">
          {t('submission_guidelines')}
        </h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• {t('guideline_unique')}</li>
          <li>• {t('guideline_descriptive')}</li>
          <li>• {t('guideline_quality_images')}</li>
          <li>• {t('guideline_appropriate')}</li>
          <li>• {t('guideline_review_process')}</li>
        </ul>
      </div>
    </div>
  );
};

export default CategorySubmission;
