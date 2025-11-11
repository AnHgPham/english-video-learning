'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../providers';
import apiClient, { Clip } from '@/lib/api-client';

export default function MyClipsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [quota, setQuota] = useState<{ used: number; limit: number; remaining: number } | null>(
    null
  );

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      fetchClips();
      fetchQuota();
    }
  }, [user, authLoading, router, page, statusFilter]);

  const fetchClips = async () => {
    try {
      setLoading(true);
      const response = await apiClient.clips.list({
        page,
        pageSize: 20,
        status: statusFilter || undefined,
      });
      setClips(response.items);
      setTotalPages(response.totalPages);
    } catch (error) {
      console.error('Failed to fetch clips:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchQuota = async () => {
    try {
      const data = await apiClient.clips.getQuota();
      setQuota(data);
    } catch (error) {
      console.error('Failed to fetch quota:', error);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiClient.clips.delete(id);
      setDeleteConfirm(null);
      fetchClips();
      fetchQuota();
    } catch (error) {
      console.error('Failed to delete clip:', error);
      alert('Failed to delete clip');
    }
  };

  const handleVisibilityToggle = async (id: number, currentVisibility: string) => {
    const newVisibility = currentVisibility === 'private' ? 'public' : 'private';
    try {
      await apiClient.clips.updateVisibility(id, newVisibility as any);
      fetchClips();
    } catch (error) {
      console.error('Failed to update visibility:', error);
      alert('Failed to update visibility');
    }
  };

  const formatDuration = (startTime: number, endTime: number) => {
    const duration = endTime - startTime;
    return `${duration.toFixed(1)}s`;
  };

  const formatTimestamp = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading clips...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">My Clips</h1>
            <nav className="flex items-center gap-4">
              <a href="/" className="text-gray-700 hover:text-primary">
                Home
              </a>
              <a href="/vocabulary" className="text-gray-700 hover:text-primary">
                Vocabulary
              </a>
              {user.role === 'admin' && (
                <a href="/admin" className="text-gray-700 hover:text-primary">
                  Admin
                </a>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Quota Card */}
        {quota && (
          <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold mb-2">Clip Quota</h2>
                <p className="text-blue-100">
                  You have created {quota.used} out of {quota.limit} clips
                </p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold">{quota.remaining}</p>
                <p className="text-blue-100">remaining</p>
              </div>
            </div>
            <div className="mt-4 w-full bg-blue-400 rounded-full h-2">
              <div
                className="bg-white h-2 rounded-full transition-all duration-300"
                style={{ width: `${(quota.used / quota.limit) * 100}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">Status:</label>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setStatusFilter('');
                  setPage(1);
                }}
                className={`px-4 py-2 rounded-lg text-sm ${
                  statusFilter === ''
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                All
              </button>
              <button
                onClick={() => {
                  setStatusFilter('completed');
                  setPage(1);
                }}
                className={`px-4 py-2 rounded-lg text-sm ${
                  statusFilter === 'completed'
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Completed
              </button>
              <button
                onClick={() => {
                  setStatusFilter('processing');
                  setPage(1);
                }}
                className={`px-4 py-2 rounded-lg text-sm ${
                  statusFilter === 'processing'
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Processing
              </button>
              <button
                onClick={() => {
                  setStatusFilter('failed');
                  setPage(1);
                }}
                className={`px-4 py-2 rounded-lg text-sm ${
                  statusFilter === 'failed'
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Failed
              </button>
            </div>
          </div>
        </div>

        {/* Clips Grid */}
        {clips.length === 0 ? (
          <div className="text-center py-12">
            <svg
              className="w-16 h-16 text-gray-300 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
              />
            </svg>
            <p className="text-gray-500 text-lg">No clips created yet</p>
            <p className="text-gray-400 text-sm mt-2">
              Watch videos and create clips to save your favorite moments
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {clips.map((clip) => (
                <div key={clip.id} className="bg-white rounded-lg shadow-sm overflow-hidden">
                  {/* Clip Preview */}
                  <div className="relative w-full h-48 bg-gray-200">
                    {clip.clipUrl ? (
                      <video
                        src={clip.clipUrl}
                        className="w-full h-full object-cover"
                        controls
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <div className="text-center">
                          {clip.status === 'processing' && (
                            <>
                              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
                              <p className="text-sm text-gray-500">Processing...</p>
                            </>
                          )}
                          {clip.status === 'failed' && (
                            <p className="text-sm text-red-500">Processing failed</p>
                          )}
                          {clip.status === 'pending' && (
                            <p className="text-sm text-gray-500">Pending...</p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Status Badge */}
                    <div className="absolute top-2 right-2">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          clip.status === 'completed'
                            ? 'bg-green-500 text-white'
                            : clip.status === 'processing'
                            ? 'bg-blue-500 text-white'
                            : clip.status === 'failed'
                            ? 'bg-red-500 text-white'
                            : 'bg-gray-500 text-white'
                        }`}
                      >
                        {clip.status}
                      </span>
                    </div>
                  </div>

                  {/* Clip Info */}
                  <div className="p-4">
                    <h3 className="font-semibold text-gray-900 mb-2 line-clamp-1">
                      {clip.title}
                    </h3>

                    <div className="flex items-center justify-between text-sm text-gray-600 mb-3">
                      <span>
                        {formatTimestamp(clip.startTime)} - {formatTimestamp(clip.endTime)}
                      </span>
                      <span>{formatDuration(clip.startTime, clip.endTime)}</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <button
                        onClick={() => handleVisibilityToggle(clip.id, clip.visibility)}
                        className={`px-3 py-1 rounded text-xs ${
                          clip.visibility === 'public'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {clip.visibility === 'public' ? 'Public' : 'Private'}
                      </button>

                      <div className="flex items-center gap-2">
                        {deleteConfirm === clip.id ? (
                          <>
                            <button
                              onClick={() => handleDelete(clip.id)}
                              className="text-red-600 hover:text-red-800 text-sm font-medium"
                            >
                              Confirm
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="text-gray-600 hover:text-gray-800 text-sm"
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirm(clip.id)}
                            className="text-red-600 hover:text-red-800 text-sm"
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
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
