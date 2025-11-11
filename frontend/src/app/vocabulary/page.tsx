'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../providers';
import apiClient, { Vocabulary } from '@/lib/api-client';

export default function VocabularyPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [words, setWords] = useState<Vocabulary[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [masteryFilter, setMasteryFilter] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      fetchVocabulary();
      fetchStats();
    }
  }, [user, authLoading, router, page, searchQuery, masteryFilter]);

  const fetchVocabulary = async () => {
    try {
      setLoading(true);
      const response = await apiClient.vocabulary.list({
        page,
        pageSize: 20,
        search: searchQuery || undefined,
        mastery: masteryFilter || undefined,
      });
      setWords(response.items);
      setTotalPages(response.totalPages);
    } catch (error) {
      console.error('Failed to fetch vocabulary:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await apiClient.vocabulary.getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiClient.vocabulary.delete(id);
      setDeleteConfirm(null);
      fetchVocabulary();
      fetchStats();
    } catch (error) {
      console.error('Failed to delete word:', error);
      alert('Failed to delete word');
    }
  };

  const handleMasteryUpdate = async (id: number, newMastery: string) => {
    try {
      await apiClient.vocabulary.update(id, { mastery: newMastery as any });
      fetchVocabulary();
      fetchStats();
    } catch (error) {
      console.error('Failed to update mastery:', error);
      alert('Failed to update mastery level');
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading vocabulary...</p>
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
            <h1 className="text-2xl font-bold text-gray-900">My Vocabulary</h1>
            <nav className="flex items-center gap-4">
              <a href="/" className="text-gray-700 hover:text-primary">
                Home
              </a>
              <a href="/my-clips" className="text-gray-700 hover:text-primary">
                My Clips
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
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white p-4 rounded-lg shadow-sm">
              <p className="text-sm text-gray-600">Total Words</p>
              <p className="text-3xl font-bold text-gray-900">{stats.total}</p>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg shadow-sm">
              <p className="text-sm text-yellow-700">Learning</p>
              <p className="text-3xl font-bold text-yellow-900">{stats.byMastery?.learning || 0}</p>
            </div>
            <div className="bg-blue-50 p-4 rounded-lg shadow-sm">
              <p className="text-sm text-blue-700">Familiar</p>
              <p className="text-3xl font-bold text-blue-900">{stats.byMastery?.familiar || 0}</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg shadow-sm">
              <p className="text-sm text-green-700">Mastered</p>
              <p className="text-3xl font-bold text-green-900">{stats.byMastery?.mastered || 0}</p>
            </div>
          </div>
        )}

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
                placeholder="Search words..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Mastery Level
              </label>
              <select
                value={masteryFilter}
                onChange={(e) => {
                  setMasteryFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="">All Levels</option>
                <option value="learning">Learning</option>
                <option value="familiar">Familiar</option>
                <option value="mastered">Mastered</option>
              </select>
            </div>
          </div>
        </div>

        {/* Vocabulary List */}
        <div className="bg-white rounded-lg shadow-sm">
          {words.length === 0 ? (
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
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
              <p className="text-gray-500 text-lg">No vocabulary saved yet</p>
              <p className="text-gray-400 text-sm mt-2">
                Start watching videos and select words to save them
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Word
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Definition
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Translation
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Mastery
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Reviewed
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {words.map((word) => (
                      <tr key={word.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <p className="font-semibold text-gray-900">{word.word}</p>
                          {word.example && (
                            <p className="text-sm text-gray-500 italic mt-1">"{word.example}"</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-gray-600 text-sm">
                          {word.definition || '-'}
                        </td>
                        <td className="px-4 py-3 text-gray-600 text-sm">
                          {word.translation || '-'}
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={word.mastery}
                            onChange={(e) => handleMasteryUpdate(word.id, e.target.value)}
                            className={`px-2 py-1 rounded-full text-xs border-0 ${
                              word.mastery === 'mastered'
                                ? 'bg-green-100 text-green-800'
                                : word.mastery === 'familiar'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}
                          >
                            <option value="learning">Learning</option>
                            <option value="familiar">Familiar</option>
                            <option value="mastered">Mastered</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 text-gray-600 text-sm">
                          {word.reviewCount} times
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-2">
                            {word.videoId && (
                              <a
                                href={`/watch/${word.videoId}`}
                                className="text-blue-600 hover:text-blue-800 text-sm"
                              >
                                Video
                              </a>
                            )}
                            {deleteConfirm === word.id ? (
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => handleDelete(word.id)}
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
                                onClick={() => setDeleteConfirm(word.id)}
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
