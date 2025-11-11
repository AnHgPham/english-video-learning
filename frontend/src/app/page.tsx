'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import apiClient, { Video } from '@/lib/api-client';
import { useAuth } from './providers';

export default function HomePage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({
    level: '',
    search: '',
  });

  useEffect(() => {
    fetchVideos();
  }, [page, filters]);

  const fetchVideos = async () => {
    try {
      setLoading(true);
      const response = await apiClient.videos.list({
        page,
        pageSize: 12,
        level: filters.level || undefined,
        search: filters.search || undefined,
      });
      setVideos(response.items);
      setTotalPages(response.totalPages);
    } catch (error) {
      console.error('Failed to fetch videos:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters({ ...filters, search: e.target.value });
    setPage(1);
  };

  const handleLevelChange = (level: string) => {
    setFilters({ ...filters, level });
    setPage(1);
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              English Video Learning
            </h1>
            <nav className="flex items-center gap-4">
              <a href="/search" className="text-gray-700 hover:text-primary">
                Search
              </a>
              {user ? (
                <>
                  <a href="/vocabulary" className="text-gray-700 hover:text-primary">
                    Vocabulary
                  </a>
                  <a href="/my-clips" className="text-gray-700 hover:text-primary">
                    My Clips
                  </a>
                  {user.role === 'admin' && (
                    <a href="/admin" className="text-gray-700 hover:text-primary">
                      Admin
                    </a>
                  )}
                  <button
                    onClick={() => apiClient.auth.logout()}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <a
                  href="/login"
                  className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                >
                  Login
                </a>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="mb-8 space-y-4">
          <div>
            <input
              type="text"
              placeholder="Search videos..."
              value={filters.search}
              onChange={handleSearchChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => handleLevelChange('')}
              className={`px-4 py-2 rounded-lg ${
                filters.level === ''
                  ? 'bg-primary text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              All Levels
            </button>
            {['A1', 'A2', 'B1', 'B2', 'C1', 'C2'].map((level) => (
              <button
                key={level}
                onClick={() => handleLevelChange(level)}
                className={`px-4 py-2 rounded-lg ${
                  filters.level === level
                    ? 'bg-primary text-white'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        {/* Video Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg shadow-sm overflow-hidden animate-pulse">
                <div className="w-full h-48 bg-gray-200"></div>
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-3 bg-gray-200 rounded w-full"></div>
                  <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                </div>
              </div>
            ))}
          </div>
        ) : videos.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">No videos found</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {videos.map((video) => (
                <a
                  key={video.id}
                  href={`/watch/${video.slug}`}
                  className="bg-white rounded-lg shadow-sm overflow-hidden hover:shadow-md transition-shadow"
                >
                  <div className="relative w-full h-48 bg-gray-200">
                    {video.thumbnailUrl ? (
                      <img
                        src={video.thumbnailUrl}
                        alt={video.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400">
                        No thumbnail
                      </div>
                    )}
                    <div className="absolute top-2 right-2 bg-black/70 text-white px-2 py-1 rounded text-sm">
                      {video.level}
                    </div>
                  </div>
                  <div className="p-4">
                    <h3 className="font-semibold text-lg mb-2 line-clamp-2">
                      {video.title}
                    </h3>
                    {video.description && (
                      <p className="text-gray-600 text-sm line-clamp-2 mb-2">
                        {video.description}
                      </p>
                    )}
                    <div className="flex items-center justify-between text-sm text-gray-500">
                      <span>{video.viewCount} views</span>
                      {video.duration && (
                        <span>{Math.floor(video.duration / 60)}:{(video.duration % 60).toString().padStart(2, '0')}</span>
                      )}
                    </div>
                  </div>
                </a>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex justify-center gap-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Previous
                </button>
                <span className="px-4 py-2 bg-white border border-gray-300 rounded-lg">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
