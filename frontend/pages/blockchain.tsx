import { GetStaticProps } from 'next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import { useTranslation } from 'next-i18next';
import Layout from '@/components/Layout';
import { BlockchainWallet } from '@/components/BlockchainWallet';

export default function BlockchainPage() {
  const { t } = useTranslation('common');

  return (
    <Layout
      title={t('blockchain.title')}
      description={t('blockchain.description')}
    >
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            {t('blockchain.title')}
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 mb-6">
            {t('blockchain.subtitle')}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <BlockchainWallet />
          </div>
          
          <div className="space-y-6">
            {/* Features Overview */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                {t('blockchain.features.title')}
              </h3>
              <ul className="space-y-3">
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-green-500 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('blockchain.features.wallet')}
                  </span>
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-blue-500 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .434-3.235-1.18l-2.344 2.344C5.434 10.76 5 9.657 5 8c0-1.657.434-3 1.18-3.235l2.344-2.344C8.566 2.24 9.343 2 11c1.657 0 3 .434 3.235 1.18l2.344 2.344C18.566 13.76 19 14.657 19 16c0 1.657-.434 3-1.18 3.235-2.344l-2.344-2.344C13.434 9.76 12.657 9 11 9c-1.657 0-3 .434-3.235 1.18l-2.344 2.344C5.434 10.76 5 9.657 5 8c0-1.657.434-3 1.18-3.235l2.344-2.344C8.566 2.24 9.343 2 11c1.657 0 3 .434 3.235 1.18l2.344 2.344C18.566 13.76 19 14.657 19 16C0 1.657-.434 3-1.18 3.235-2.344l-2.344-2.344z" />
                  </svg>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('blockchain.features.tokens')}
                  </span>
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-purple-500 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2v2a2 2 0 01-2 2H9a2 2 0 01-2-2V7a2 2 0 012-2zm0 10a2 2 0 002 2v2a2 2 0 01-2 2H9a2 2 0 01-2-2v-2a2 2 0 00-2-2z" />
                  </svg>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('blockchain.features.vesting')}
                  </span>
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-orange-500 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2V6a2 2 0 002 2zm.707 3.293a1 1 0 01-1.414 0L9 16.586 7.707a1 1 0 01-1.414 0l-4.586 4.586a1 1 0 011.414 1.414L6.586 18.414a1 1 0 011.414 0l4.586-4.586a1 1 0 011.414-1.414z" />
                  </svg>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('blockchain.features.governance')}
                  </span>
                </li>
              </ul>
            </div>

            {/* How It Works */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                {t('blockchain.how.title')}
              </h3>
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    {t('blockchain.how.step1.title')}
                  </h4>
                  <p className="text-gray-600 dark:text-gray-400">
                    {t('blockchain.how.step1.description')}
                  </p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    {t('blockchain.how.step2.title')}
                  </h4>
                  <p className="text-gray-600 dark:text-gray-400">
                    {t('blockchain.how.step2.description')}
                  </p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    {t('blockchain.how.step3.title')}
                  </h4>
                  <p className="text-gray-600 dark:text-gray-400">
                    {t('blockchain.how.step3.description')}
                  </p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    {t('blockchain.how.step4.title')}
                  </h4>
                  <p className="text-gray-600 dark:text-gray-400">
                    {t('blockchain.how.step4.description')}
                  </p>
                </div>
              </div>
            </div>

            {/* Token Info */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                {t('blockchain.token.title')}
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">{t('blockchain.token.name')}</span>
                  <span className="font-medium text-gray-900 dark:text-white">FLV</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">{t('blockchain.token.decimals')}</span>
                  <span className="font-medium text-gray-900 dark:text-white">7</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">{t('blockchain.token.network')}</span>
                  <span className="font-medium text-gray-900 dark:text-white">Stellar Testnet</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">{t('blockchain.token.contract')}</span>
                  <span className="text-xs font-mono text-gray-500 dark:text-gray-400 break-all">
                    {process.env.NEXT_PUBLIC_CONTRACT_ADDRESS || 'Coming Soon'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export const getStaticProps: GetStaticProps = async ({ locale }) => {
  return {
    props: {
      ...(await serverSideTranslations(locale || 'en', ['common'])),
    },
  };
};
