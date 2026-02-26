import React, { useState, useEffect } from 'react';
import { useTranslation } from 'next-i18next';

interface Category {
  id: string;
  name: string;
  description: string;
  submitted_by: string;
  submitted_at: string;
  status: 'pending' | 'approved' | 'rejected' | 'in_training';
  images: string[];
  votes_up: number;
  votes_down: number;
  moderator_notes?: string;
  approved_by?: string;
  approved_at?: string;
}

interface CategoryListProps {
  status?: 'pending' | 'approved' | 'rejected' | 'all';
  onVote?: (categoryId: string, voteType: 'upvote' | 'downvote') => void;
  onModerate?: (categoryId: string, action: 'approve' | 'reject', notes?: string) => void;
  showActions?: boolean;
  limit?: number;
}

const CategoryList: React.FC<CategoryListProps> = ({ 
  status = 'pending', 
  onVote, 
  onModerate, 
  showActions = false,
  limit = 20 
}) => {
  const { t } = useTranslation('common');
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const fetchCategories = async (pageNum: number = 0, reset: boolean = false) => {
    try {
      setLoading(true);
      const statusParam = status === 'all' ? '' : `?status=${status}`;
      const limitParam = `&limit=${limit}&offset=${pageNum * limit}`;
      const response = await fetch(`/api/categories${statusParam}${limitParam}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch categories');
      }
      
      const data = await response.json();
      const newCategories = data.categories || [];
      
      if (reset) {
        setCategories(newCategories);
      } else {
        setCategories(prev => [...prev, ...newCategories]);
      }
      
      setHasMore(newCategories.length === limit);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories(0, true);
  }, [status]);

  const loadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchCategories(nextPage, false);
  };

  const handleVote = async (categoryId: string, voteType: 'upvote' | 'downvote') => {
    if (!onVote) return;

    try {
      const userId = localStorage.getItem('userId') || `user_${Date.now()}`;
      localStorage.setItem('userId', userId);

      const response = await fetch(`/api/categories/${categoryId}/vote`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          vote_type: voteType,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to vote');
      }

      // Update local state
      setCategories(prev => prev.map(cat => {
        if (cat.id === categoryId) {
          return {
            ...cat,
            votes_up: voteType === 'upvote' ? cat.votes_up + 1 : cat.votes_up,
            votes_down: voteType === 'downvote' ? cat.votes_down + 1 : cat.votes_down,
          };
        }
        return cat;
      }));

      onVote(categoryId, voteType);
    } catch (err) {
      console.error('Vote error:', err);
      // You might want to show a toast notification here
    }
  };

  const handleModerate = async (categoryId: string, action: 'approve' | 'reject') => {
    if (!onModerate) return;

    const notes = action === 'reject' 
      ? prompt('Please provide rejection reason:')
      : prompt('Optional notes for approval:');

    if (action === 'reject' && !notes) {
      return; // Require notes for rejection
    }

    try {
      const moderatorId = localStorage.getItem('moderatorId') || `mod_${Date.now()}`;
      localStorage.setItem('moderatorId', moderatorId);

      const response = await fetch(`/api/categories/${categoryId}/moderate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          moderator_id: moderatorId,
          action,
          notes: notes || '',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to moderate');
      }

      // Update local state
      setCategories(prev => prev.map(cat => {
        if (cat.id === categoryId) {
          return {
            ...cat,
            status: action === 'approve' ? 'approved' : 'rejected',
            approved_by: moderatorId,
            approved_at: new Date().toISOString(),
            moderator_notes: notes || '',
          };
        }
        return cat;
      }));

      onModerate(categoryId, action, notes);
    } catch (err) {
      console.error('Moderation error:', err);
      // You might want to show a toast notification here
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'approved': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'in_training': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading && categories.length === 0) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-red-600 mb-4">{error}</div>
        <button 
          onClick={() => fetchCategories(0, true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
        >
          {t('retry')}
        </button>
      </div>
    );
  }

  if (categories.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>{t('no_categories_found')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">
        {t(`${status}_categories`)}
      </h2>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {categories.map((category) => (
          <div key={category.id} className="bg-white rounded-lg shadow-md overflow-hidden">
            {/* Images */}
            <div className="relative h-48 bg-gray-200">
              {category.images.length > 0 ? (
                <img
                  src={`/uploads/${category.images[0]}`}
                  alt={category.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400">
                  <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              )}
              
              {/* Status Badge */}
              <div className="absolute top-2 right-2">
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(category.status)}`}>
                  {t(category.status)}
                </span>
              </div>

              {/* Image Count */}
              {category.images.length > 1 && (
                <div className="absolute bottom-2 left-2 bg-black bg-opacity-50 text-white px-2 py-1 rounded text-xs">
                  +{category.images.length - 1} {t('more_images')}
                </div>
              )}
            </div>

            {/* Content */}
            <div className="p-4">
              <h3 className="font-semibold text-lg text-gray-800 mb-2">
                {category.name}
              </h3>
              
              <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                {category.description}
              </p>

              <div className="text-xs text-gray-500 mb-3">
                <p>{t('submitted_by')}: {category.submitted_by}</p>
                <p>{formatDate(category.submitted_at)}</p>
              </div>

              {/* Voting */}
              {status === 'pending' && onVote && (
                <div className="flex items-center justify-between mb-3">
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleVote(category.id, 'upvote')}
                      className="flex items-center space-x-1 px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                      </svg>
                      <span className="text-sm">{category.votes_up}</span>
                    </button>
                    
                    <button
                      onClick={() => handleVote(category.id, 'downvote')}
                      className="flex items-center space-x-1 px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                      <span className="text-sm">{category.votes_down}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Moderator Actions */}
              {showActions && status === 'pending' && onModerate && (
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleModerate(category.id, 'approve')}
                    className="flex-1 bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 transition-colors"
                  >
                    {t('approve')}
                  </button>
                  <button
                    onClick={() => handleModerate(category.id, 'reject')}
                    className="flex-1 bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition-colors"
                  >
                    {t('reject')}
                  </button>
                </div>
              )}

              {/* Moderator Notes */}
              {category.moderator_notes && (
                <div className="mt-3 p-2 bg-gray-100 rounded text-xs text-gray-600">
                  <strong>{t('moderator_notes')}:</strong> {category.moderator_notes}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Load More */}
      {hasMore && (
        <div className="text-center mt-8">
          <button
            onClick={loadMore}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? t('loading') : t('load_more')}
          </button>
        </div>
      )}
    </div>
  );
};

export default CategoryList;
