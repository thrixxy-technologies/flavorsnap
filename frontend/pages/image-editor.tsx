import React from 'react';
import ImageEditor from '../components/ImageEditor';
import Layout from '../components/Layout';
import SEOHead from '../components/SEOHead';

const ImageEditorPage: React.FC = () => {
  return (
    <Layout>
      <SEOHead
        metadata={{
          title: 'Image Editor - FlavorSnap',
          description: 'Advanced image editing tools with filters, adjustments, and annotation capabilities for food images.',
          keywords: 'image editor, photo editing, filters, food photography, image processing',
          type: 'website',
        }}
      />
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Image Editor</h1>
          <p className="text-gray-600">
            Edit your food images with professional tools including filters, brightness/contrast adjustments,
            cropping, rotation, and annotation features.
          </p>
        </div>
        <ImageEditor />
      </div>
    </Layout>
  );
};

export default ImageEditorPage;