import React, { useState } from 'react';
import { GetStaticProps } from 'next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import { useTranslation } from 'next-i18next';
import CategorySubmission, { CategorySubmissionData } from '../components/CategorySubmission';
import CategoryList from '../components/CategoryList';
import Layout from '../components/Layout';

const CategoriesPage: React.FC = () => {
  const { t } = useTranslation('common');
  const [activeTab, setActiveTab] = useState<'submit' | 'pending' | 'approved' | 'rejected'>('submit');
  const [submissionLoading, setSubmissionLoading] = useState(false);
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);

  const handleSubmit = async (data: CategorySubmissionData) => {
    setSubmissionLoading(true);
    setSubmissionMessage(null);

    try {
      const formData = new FormData();
      formData.append('name', data.name);
      formData.append('description', data.description);
      formData.append('submitted_by', data.submitted_by);
      
      data.images.forEach((image) => {
        formData.append('images', image);
      });

      const response = await fetch('/api/categories/submit', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Submission failed');
      }

      const result = await response.json();
      setSubmissionMessage(t('submission_success'));
      
      // Reset form after successful submission
      setTimeout(() => {
        setSubmissionMessage(null);
      }, 5000);

    } catch (error) {
      setSubmissionMessage(error instanceof Error ? error.message : t('submission_error'));
    } finally {
      setSubmissionLoading(false);
    }
  };

  const tabs = [
    { id: 'submit', label: t('submit_category'), icon: '📝' },
    { id: 'pending', label: t('pending_review'), icon: '⏳' },
    { id: 'approved', label: t('approved'), icon: '✅' },
    { id: 'rejected', label: t('rejected'), icon: '❌' },
  ] as const;

  return (
    <Layout 
      title="Food Categories - FlavorSnap" 
      description="Submit and review new food categories for the AI model"
    >
      <div className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-800">
          {t('food_categories')}
        </h1>

        {/* Tab Navigation */}
        <div className="flex flex-wrap justify-center mb-8 border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Submission Message */}
        {submissionMessage && (
          <div className={`mb-6 p-4 rounded-md text-center ${
            submissionMessage.includes(t('submission_success'))
              ? 'bg-green-100 text-green-800 border border-green-200'
              : 'bg-red-100 text-red-800 border border-red-200'
          }`}>
            {submissionMessage}
          </div>
        )}

        {/* Tab Content */}
        <div className="min-h-screen">
          {activeTab === 'submit' && (
            <CategorySubmission 
              onSubmit={handleSubmit} 
              loading={submissionLoading}
            />
          )}

          {activeTab === 'pending' && (
            <CategoryList 
              status="pending"
              onVote={(categoryId, voteType) => {
                console.log(`Voted ${voteType} on category ${categoryId}`);
              }}
            />
          )}

          {activeTab === 'approved' && (
            <CategoryList status="approved" />
          )}

          {activeTab === 'rejected' && (
            <CategoryList status="rejected" />
          )}
        </div>

        {/* Statistics Section */}
        <div className="mt-12 bg-gray-50 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">
            {t('community_statistics')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="text-2xl font-bold text-blue-600">--</div>
              <div className="text-sm text-gray-600">{t('total_submissions')}</div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="text-2xl font-bold text-yellow-600">--</div>
              <div className="text-sm text-gray-600">{t('pending_review')}</div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="text-2xl font-bold text-green-600">--</div>
              <div className="text-sm text-gray-600">{t('approved_categories')}</div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="text-2xl font-bold text-purple-600">--</div>
              <div className="text-sm text-gray-600">{t('in_training')}</div>
            </div>
          </div>
        </div>

        {/* Guidelines Section */}
        <div className="mt-8 bg-blue-50 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4 text-blue-800">
            {t('community_guidelines')}
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-blue-700 mb-2">{t('for_submitters')}</h3>
              <ul className="text-sm text-blue-600 space-y-1">
                <li>• {t('submit_original_categories')}</li>
                <li>• {t('provide_clear_descriptions')}</li>
                <li>• {t('upload_high_quality_images')}</li>
                <li>• {t('be_respectful_community')}</li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-blue-700 mb-2">{t('for_voters')}</h3>
              <ul className="text-sm text-blue-600 space-y-1">
                <li>• {t('vote_thoughtfully')}</li>
                <li>• {t('consider_cultural_significance')}</li>
                <li>• {t('verify_image_quality')}</li>
                <li>• {t('avoid_bias')}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export const getStaticProps: GetStaticProps = async ({ locale }) => ({
  props: {
    ...(await serverSideTranslations(locale ?? 'en', ['common'])),
  },
});

export default CategoriesPage;
