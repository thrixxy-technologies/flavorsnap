import { useState, useCallback, useEffect } from 'react';

export interface SocialActivity {
  id: string;
  type: 'post' | 'like' | 'follow' | 'share';
  user: string;
  target?: string;
  timestamp: string;
  content?: string;
}

export interface SocialStats {
  followers: number;
  following: number;
  posts: number;
}

export const useSocialFeatures = (userId: string) => {
  const [isFollowing, setIsFollowing] = useState(false);
  const [stats, setStats] = useState<SocialStats>({ followers: 0, following: 0, posts: 0 });
  const [activities, setActivities] = useState<SocialActivity[]>([]);
  const [notifications, setNotifications] = useState<SocialActivity[]>([]);
  const [loading, setLoading] = useState(false);

  // Mock fetching data
  useEffect(() => {
    if (!userId) return;

    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      setStats({
        followers: Math.floor(Math.random() * 1000),
        following: Math.floor(Math.random() * 500),
        posts: Math.floor(Math.random() * 100),
      });
      setActivities([
        { id: '1', type: 'post', user: 'You', content: 'Just cooked a delicious meal!', timestamp: new Date().toISOString() },
        { id: '2', type: 'like', user: 'Alex', target: 'Your post', timestamp: new Date().toISOString() },
      ]);
      setNotifications([
        { id: 'n1', type: 'follow', user: 'Sarah', timestamp: new Date().toISOString() },
      ]);
      setLoading(false);
    }, 1000);
  }, [userId]);

  const toggleFollow = useCallback(async () => {
    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      setIsFollowing(prev => !prev);
      setStats(prev => ({
        ...prev,
        followers: isFollowing ? prev.followers - 1 : prev.followers + 1,
      }));
      setLoading(false);
    }, 500);
  }, [isFollowing]);

  const shareProfile = useCallback((platform: 'twitter' | 'facebook' | 'linkedin') => {
    const url = typeof window !== 'undefined' ? window.location.href : '';
    const text = `Check out my profile on FlavorSnap!`;
    const shareUrl = `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
    window.open(shareUrl, '_blank');
  }, []);

  return {
    isFollowing,
    stats,
    activities,
    notifications,
    loading,
    toggleFollow,
    shareProfile,
  };
};
