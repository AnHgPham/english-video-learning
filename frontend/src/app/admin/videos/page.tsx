'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../providers';
import apiClient, { Video } from '@/lib/api-client';

export default function AdminVideosPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  useEffect(() => {
    if (!authLoading && (!user || user.role !== 'admin')) {
      router.push('/');
      return;
    }

    if (user?.role === 'admin') {
      fetchVideos();
    }
  }, [user, authLoading, router, page, statusFilter, searchQuery]);

  const fetchVideos = async () => {
    try {
      setLoading(true);
      const response = await apiClient.admin.listVideos({
        page,
        pageSize: 20,
        status: statusFilter || undefined,
        search: searchQuery || undefined,
      });
      setVideos(response.items);
      setTotalPages(response.totalPages);
    } catch (error) {
      console.error('Failed to fetch videos:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (videoId: number) => {
    try {
      await apiClient.admin.deleteVideo(videoId);
      setDeleteConfirm(null);
      fetchVideos();
    } catch (error) {
      console.error('Failed to delete video:', error);
      alert('Failed to delete video');
    }
  };

  const handleStatusChange = async (videoId: number, newStatus: string) => {
    try {
      await apiClient.admin.updateVideo(videoId, { status: newStatus as any });
      fetchVideos();
    } catch (error) {
      console.error('Failed to update video status:', error);
      alert('Failed to update video status');
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading videos...</p>
        </div>
      </div>
    );
  }

  if (!user || user.role !== 'admin') {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">Video Management</h1>
            <nav className="flex items-center gap-4">
              <a href="/admin" className="text-gray-700 hover:text-primary">
                Dashboard
              </a>
              <a
                href="/admin/videos/upload"
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
              >
                Upload Video
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                placeholder="Search by title..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="">All Status</option>
                <option value="draft">Draft</option>
                <option value="processing">Processing</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>
        </div>

        {/* Videos Table */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          {videos.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">No videos found</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Video
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Level
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Status
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Views
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Created
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {videos.map((video) => (
                      <tr key={video.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-16 h-10 bg-gray-200 rounded overflow-hidden flex-shrink-0">
                              {video.thumbnailUrl ? (
                                <img
                                  src={video.thumbnailUrl}
                                  alt={video.title}
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">
                                  No thumb
                                </div>
                              )}
                            </div>
                            <div>
                              <p className="font-medium text-gray-900 line-clamp-1">
                                {video.title}
                              </p>
                              <p className="text-sm text-gray-500">{video.slug}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                            {video.level}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={video.status}
                            onChange={(e) => handleStatusChange(video.id, e.target.value)}
                            className={`px-2 py-1 rounded-full text-xs border-0 ${
                              video.status === 'published'
                                ? 'bg-green-100 text-green-800'
                                : video.status === 'processing'
                                ? 'bg-blue-100 text-blue-800'
                                : video.status === 'archived'
                                ? 'bg-gray-100 text-gray-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}
                          >
                            <option value="draft">Draft</option>
                            <option value="processing">Processing</option>
                            <option value="published">Published</option>
                            <option value="archived">Archived</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 text-gray-600">{video.viewCount}</td>
                        <td className="px-4 py-3 text-gray-600 text-sm">
                          {new Date(video.createdAt).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-2">
                            <a
                              href={`/watch/${video.slug}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:text-blue-800 text-sm"
                            >
                              View
                            </a>
                            {deleteConfirm === video.id ? (
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => handleDelete(video.id)}
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
                              </div>
                            ) : (
                              <button
                                onClick={() => setDeleteConfirm(video.id)}
                                className="text-red-600 hover:text-red-800 text-sm"
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="border-t px-4 py-3 flex items-center justify-between">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-gray-600">
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
        </div>
      </main>
    </div>
  );
}
