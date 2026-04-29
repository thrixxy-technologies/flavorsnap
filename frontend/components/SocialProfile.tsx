import React from 'react';
import { useSocialFeatures } from '../hooks/useSocialFeatures';
import { formatSocialStats } from '../utils/socialUtils';

interface SocialProfileProps {
  userId: string;
  username: string;
  bio: string;
  avatarUrl: string;
}

const SocialProfile: React.FC<SocialProfileProps> = ({ userId, username, bio, avatarUrl }) => {
  const { isFollowing, stats, activities, notifications, loading, toggleFollow, shareProfile } = useSocialFeatures(userId);

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white dark:bg-gray-900 rounded-3xl shadow-2xl overflow-hidden transition-all duration-300 hover:shadow-orange-500/20">
      {/* Header / Cover */}
      <div className="h-48 bg-gradient-to-r from-orange-400 via-pink-500 to-purple-600 rounded-2xl relative">
        <div className="absolute -bottom-16 left-8 p-1 bg-white dark:bg-gray-900 rounded-full border-4 border-white dark:border-gray-900 shadow-xl">
          <img src={avatarUrl} alt={username} className="w-32 h-32 rounded-full object-cover" />
        </div>
      </div>

      {/* Profile Info */}
      <div className="mt-20 px-8 flex flex-col md:flex-row justify-between items-start gap-6">
        <div className="flex-1">
          <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white flex items-center gap-2">
            {username}
            <span className="bg-blue-500 text-white p-1 rounded-full text-[10px]">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.64.304 1.24.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </span>
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2 text-lg italic leading-relaxed">
            {bio}
          </p>
          
          <div className="flex gap-6 mt-6">
            <div className="text-center">
              <span className="block text-2xl font-black text-orange-500">{formatSocialStats(stats.followers)}</span>
              <span className="text-sm text-gray-500 uppercase tracking-widest font-semibold">Followers</span>
            </div>
            <div className="text-center">
              <span className="block text-2xl font-black text-orange-500">{formatSocialStats(stats.following)}</span>
              <span className="text-sm text-gray-500 uppercase tracking-widest font-semibold">Following</span>
            </div>
            <div className="text-center">
              <span className="block text-2xl font-black text-orange-500">{formatSocialStats(stats.posts)}</span>
              <span className="text-sm text-gray-500 uppercase tracking-widest font-semibold">Posts</span>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button 
            onClick={toggleFollow}
            disabled={loading}
            className={`px-8 py-3 rounded-full font-bold text-lg transition-all duration-300 transform hover:scale-105 active:scale-95 shadow-lg ${
              isFollowing 
              ? 'bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700' 
              : 'bg-gradient-to-r from-orange-500 to-pink-600 text-white hover:from-orange-600 hover:to-pink-700 shadow-orange-500/30'
            }`}
          >
            {isFollowing ? 'Unfollow' : 'Follow'}
          </button>
          <button 
            onClick={() => shareProfile('twitter')}
            className="p-3 bg-white dark:bg-gray-800 border-2 border-gray-100 dark:border-gray-700 rounded-full text-gray-600 dark:text-gray-300 hover:text-orange-500 hover:border-orange-500 transition-all shadow-md transform hover:rotate-12"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Tabs / Activity Feed */}
      <div className="mt-12 border-t border-gray-100 dark:border-gray-800 pt-8 px-8">
        <div className="flex gap-8 mb-8 overflow-x-auto pb-2 scrollbar-hide">
          <button className="text-orange-500 font-bold border-b-4 border-orange-500 pb-2 whitespace-nowrap">Activity Feed</button>
          <button className="text-gray-400 hover:text-gray-600 font-bold pb-2 whitespace-nowrap">Photos</button>
          <button className="text-gray-400 hover:text-gray-600 font-bold pb-2 whitespace-nowrap">Favorites</button>
          <button className="text-gray-400 hover:text-gray-600 font-bold pb-2 whitespace-nowrap">Achievements</button>
        </div>

        <div className="space-y-6">
          {activities.map(activity => (
            <div key={activity.id} className="flex gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-gray-800/50 hover:bg-orange-50 dark:hover:bg-orange-900/10 transition-colors group">
              <div className="w-12 h-12 rounded-xl bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center text-orange-500 font-bold shrink-0 group-hover:scale-110 transition-transform">
                {activity.type === 'post' ? '🍽️' : activity.type === 'like' ? '❤️' : '👤'}
              </div>
              <div className="flex-1">
                <div className="flex justify-between items-start">
                  <p className="font-bold text-gray-900 dark:text-white">
                    {activity.user} <span className="font-normal text-gray-500">{activity.type === 'post' ? 'shared a new dish' : activity.type === 'like' ? `liked ${activity.target}` : 'started following you'}</span>
                  </p>
                  <span className="text-xs text-gray-400 font-medium">{new Date(activity.timestamp).toLocaleTimeString()}</span>
                </div>
                {activity.content && (
                  <p className="mt-2 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-3 rounded-xl border border-gray-100 dark:border-gray-700 shadow-sm">
                    {activity.content}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Notifications Toast Mockup */}
      {notifications.length > 0 && (
        <div className="fixed bottom-8 right-8 animate-bounce">
          <div className="bg-gradient-to-r from-orange-600 to-pink-600 text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-3">
            <span className="animate-pulse">🔔</span>
            <span className="font-bold">{notifications[0].user} followed you!</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default SocialProfile;
