import React from 'react';
import Head from 'next/head';
import SocialProfile from '../components/SocialProfile';
import { getSocialPreviewMetadata } from '../utils/socialUtils';

const ProfilePage = () => {
  const user = {
    id: 'user_123',
    username: 'ChefGourmet',
    bio: 'Exploring the world one dish at a time. Foodie, traveler, and home cook. Sharing my favorite recipes and culinary discoveries.',
    avatarUrl: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?ixlib=rb-1.2.1&auto=format&fit=crop&w=400&q=80',
  };

  const metadata = getSocialPreviewMetadata(
    `${user.username} | FlavorSnap`,
    user.bio,
    user.avatarUrl
  );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-black py-12 px-4 sm:px-6 lg:px-8">
      <Head>
        <title>{metadata.title}</title>
        <meta name="description" content={metadata.description} />
        {Object.entries(metadata).map(([key, value]) => (
          <meta key={key} property={key} content={value as string} />
        ))}
      </Head>

      <main>
        <div className="max-w-7xl mx-auto mb-12 text-center">
          <h2 className="text-sm font-black text-orange-500 uppercase tracking-[0.3em] mb-4">Social Network</h2>
          <h1 className="text-5xl font-black text-gray-900 dark:text-white mb-6">User Profile</h1>
          <p className="text-xl text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
            Connect with other food enthusiasts, share your culinary journey, and discover new flavors together.
          </p>
        </div>

        <SocialProfile 
          userId={user.id}
          username={user.username}
          bio={user.bio}
          avatarUrl={user.avatarUrl}
        />

        {/* Social Analytics Preview */}
        <div className="max-w-4xl mx-auto mt-12 grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="p-8 bg-white dark:bg-gray-900 rounded-3xl shadow-xl border border-gray-100 dark:border-gray-800">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
              <span className="text-orange-500">📊</span> Growth Analytics
            </h3>
            <div className="h-48 flex items-end gap-2 px-4">
              {[40, 70, 45, 90, 65, 80, 100].map((height, i) => (
                <div 
                  key={i} 
                  className="flex-1 bg-gradient-to-t from-orange-500 to-pink-500 rounded-t-lg transition-all duration-500 hover:opacity-80"
                  style={{ height: `${height}%` }}
                />
              ))}
            </div>
            <p className="mt-4 text-sm text-gray-500 text-center font-medium uppercase tracking-wider">Follower growth (last 7 days)</p>
          </div>

          <div className="p-8 bg-white dark:bg-gray-900 rounded-3xl shadow-xl border border-gray-100 dark:border-gray-800">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
              <span className="text-orange-500">🔒</span> Privacy Settings
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                <span className="font-semibold text-gray-700 dark:text-gray-300">Public Profile</span>
                <div className="w-12 h-6 bg-orange-500 rounded-full relative">
                  <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full shadow-sm" />
                </div>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-800 rounded-xl opacity-60">
                <span className="font-semibold text-gray-700 dark:text-gray-300">Share Activity Feed</span>
                <div className="w-12 h-6 bg-gray-300 dark:bg-gray-700 rounded-full relative">
                  <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow-sm" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ProfilePage;
