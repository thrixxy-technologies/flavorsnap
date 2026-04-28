import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import { pwaManager, ClassificationCache } from '@/lib/pwa-utils';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import type { GetStaticProps } from "next";

export default function Offline() {
  const { t } = useTranslation('common');
  const [cachedClassifications, setCachedClassifications] = useState<ClassificationCache[]>([]);

  useEffect(() => {
    // Load cached classifications
    const cached = pwaManager.getCachedClassifications();
    setCachedClassifications(cached);
  }, []);

  const handleRetry = async () => {
    const isOnline = await pwaManager.isOnline();
    if (isOnline) {
      window.location.reload();
    } else {
      // Show some UI feedback instead of just alert
      alert(t('still_offline', 'Still offline. Please check your internet connection.'));
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300 font-sans">
      <Head>
        <title>Offline - FlavorSnap</title>
        <meta name="description" content="You are currently offline" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="robots" content="noindex" />
      </Head>
      
      <main className="max-w-4xl mx-auto px-4 py-12 sm:py-20 flex flex-col items-center">
        {/* Animated Offline Icon */}
        <div className="relative mb-12 animate-pulse-slow">
          <div className="absolute inset-0 bg-indigo-500/20 rounded-full blur-3xl" />
          <div className="relative w-32 h-32 sm:w-40 sm:h-40 bg-white dark:bg-gray-800 rounded-full shadow-2xl flex items-center justify-center border-4 border-indigo-100 dark:border-indigo-900/40">
            <svg className="w-16 h-16 sm:w-20 sm:h-20 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-6xl font-black text-center mb-6 text-gray-900 dark:text-white">
          {t('youre_offline', "You're Offline")}
        </h1>
        
        <p className="text-lg sm:text-xl text-gray-500 dark:text-gray-400 text-center max-w-xl mb-12">
          {t('offline_message', "FlavorSnap is currently running on local power. You can still access your recent classification history and cached results.")}
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 mb-16 w-full max-w-md">
          <button 
            onClick={handleRetry}
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-4 px-8 rounded-2xl shadow-xl transition-all hover:scale-105 active:scale-95 font-bold text-lg"
          >
            {t('try_again', 'Try Again')}
          </button>
          <button 
            onClick={() => window.history.back()}
            className="flex-1 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 py-4 px-8 rounded-2xl shadow-lg transition-all hover:bg-gray-50 dark:hover:bg-gray-700 font-bold text-lg"
          >
            {t('go_back', 'Go Back')}
          </button>
        </div>

        {/* Cached Content Section */}
        {cachedClassifications.length > 0 ? (
          <section className="w-full animate-fade-in-up">
            <div className="flex items-center gap-4 mb-8">
              <h2 className="text-2xl font-black text-gray-900 dark:text-white uppercase tracking-wider">
                {t('available_offline', 'Cached History')}
              </h2>
              <div className="h-px flex-1 bg-gray-200 dark:bg-gray-800" />
              <span className="text-xs font-black bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 px-3 py-1 rounded-full uppercase">
                {cachedClassifications.length} Items
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {cachedClassifications.map((item, index) => (
                <div 
                  key={index} 
                  className="bg-white dark:bg-gray-800/60 backdrop-blur-md p-6 rounded-[2rem] shadow-xl border border-gray-100 dark:border-gray-700/50 group hover:-translate-y-1 transition-all duration-300"
                >
                  <div className="flex justify-between items-start mb-4">
                    <span className="text-[10px] font-black text-indigo-500 uppercase tracking-widest">
                      {new Date(item.cachedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                    <span className="text-xs font-black text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-1 rounded-lg">
                      {Math.round(item.confidence * 100)}%
                    </span>
                  </div>
                  <h3 className="text-2xl font-black text-gray-900 dark:text-white capitalize mb-2">
                    {item.food}
                  </h3>
                  {item.calories && (
                    <p className="text-sm font-bold text-gray-400 dark:text-gray-500 flex items-center gap-1.5">
                      <span>🔥</span> {item.calories} kcal
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>
        ) : (
          <div className="text-center p-12 bg-white dark:bg-gray-800/40 rounded-[3rem] border-4 border-dashed border-gray-100 dark:border-gray-800 w-full max-w-2xl">
            <p className="text-gray-400 dark:text-gray-500 font-bold text-lg">
              {t('no_offline_content', 'No cached results are available for offline browsing.')}
            </p>
          </div>
        )}
      </main>

      <footer className="w-full py-8 text-center text-gray-400 text-xs">
        &copy; {new Date().getFullYear()} FlavorSnap. {t('offline_mode_active', 'Offline Mode Active')}
      </footer>
    </div>
  );
}

export const getStaticProps: GetStaticProps = async ({ locale }) => ({
  props: {
    ...(await serverSideTranslations(locale ?? "en", ["common"])),
  },
});
