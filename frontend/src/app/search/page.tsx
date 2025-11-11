'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '../providers';
import apiClient, { SearchResult } from '@/lib/api-client';

export default function SearchPage() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [levelFilter, setLevelFilter] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);

  useEffect(() => {
    if (initialQuery) {
      performSearch();
    }
  }, [initialQuery, page, levelFilter]);

  const performSearch = async () => {
    if (!query.trim()) return;

    try {
      setLoading(true);
      const response = await apiClient.search.search({
        query: query.trim(),
        page,
        pageSize: 20,
        level: levelFilter || undefined,
      });
      setResults(response.items);
      setTotalPages(response.totalPages);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
      setPage(1);
      performSearch();
    }
  };

  const handleQueryChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value;
    setQuery(newQuery);

    // Fetch suggestions
    if (newQuery.trim().length >= 2) {
      try {
        const data = await apiClient.search.getSuggestions(newQuery.trim());
        setSuggestions(data);
      } catch (error) {
        console.error('Failed to fetch suggestions:', error);
      }
    } else {
      setSuggestions([]);
    }
  };

  const jumpToTimestamp = (videoSlug: string, timestamp: number) => {
    router.push(`/watch/${videoSlug}?t=${timestamp}`);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <a href="/" className="text-xl font-bold text-gray-900">
              English Video Learning
            </a>
            <nav className="flex items-center gap-4">
              <a href="/" className="text-gray-700 hover:text-primary">
                Home
              </a>
              {user && (
                <>
                  <a href="/vocabulary" className="text-gray-700 hover:text-primary">
                    Vocabulary
                  </a>
                  <a href="/my-clips" className="text-gray-700 hover:text-primary">
                    My Clips
                  </a>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Form */}
        <div className="mb-8">
          <form onSubmit={handleSearch} className="relative">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={query}
                  onChange={handleQueryChange}
                  placeholder="Search for words, phrases, or sentences in videos..."
                  className="w-full px-4 py-3 text-lg border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                  autoFocus
                />

                {/* Suggestions Dropdown */}
                {suggestions.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-64 overflow-y-auto">
                    {suggestions.map((suggestion, index) => (
                      <button
                        key={index}
                        type="button"
                        onClick={() => {
                          setQuery(suggestion);
                          setSuggestions([]);
                          router.push(`/search?q=${encodeURIComponent(suggestion)}`);
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-gray-50 border-b last:border-b-0"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button
                type="submit"
                className="px-8 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90"
              >
                Search
              </button>
            </div>
          </form>

          {/* Level Filter */}
          <div className="mt-4 flex gap-2 flex-wrap">
            <button
              onClick={() => {
                setLevelFilter('');
                setPage(1);
                if (query) performSearch();
              }}
              className={`px-4 py-2 rounded-lg text-sm ${
                levelFilter === ''
                  ? 'bg-primary text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              All Levels
            </button>
            {['A1', 'A2', 'B1', 'B2', 'C1', 'C2'].map((level) => (
              <button
                key={level}
                onClick={() => {
                  setLevelFilter(level);
                  setPage(1);
                  if (query) performSearch();
                }}
                className={`px-4 py-2 rounded-lg text-sm ${
                  levelFilter === level
                    ? 'bg-primary text-white'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        {/* Search Results */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Searching...</p>
          </div>
        ) : results.length === 0 && query ? (
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
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <p className="text-gray-500 text-lg">No results found for "{query}"</p>
            <p className="text-gray-400 text-sm mt-2">
              Try different keywords or check your spelling
            </p>
          </div>
        ) : results.length > 0 ? (
          <>
            <div className="mb-4 text-gray-600">
              Found {results.length} results for "{query}"
            </div>

            <div className="space-y-4">
              {results.map((result) => (
                <div
                  key={result.sentenceId}
                  className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start gap-4">
                    {/* Thumbnail */}
                    <div className="w-40 h-24 bg-gray-200 rounded overflow-hidden flex-shrink-0">
                      {result.thumbnailUrl ? (
                        <img
                          src={result.thumbnailUrl}
                          alt={result.videoTitle}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">
                          No thumbnail
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-semibold text-lg text-gray-900 mb-1">
                            {result.videoTitle}
                          </h3>
                          <div className="flex items-center gap-2 text-sm text-gray-500">
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                              {result.level}
                            </span>
                            <span>
                              {Math.floor(result.timestamp / 60)}:
                              {(result.timestamp % 60).toString().padStart(2, '0')}
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={() => jumpToTimestamp(result.videoSlug, result.timestamp)}
                          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 text-sm"
                        >
                          Watch
                        </button>
                      </div>

                      {/* Sentence Text */}
                      <p className="text-gray-800 mb-2">
                        {result.matchedPhrase ? (
                          <span
                            dangerouslySetInnerHTML={{
                              __html: result.sentenceText.replace(
                                new RegExp(result.matchedPhrase, 'gi'),
                                '<mark class="bg-yellow-200 px-1 rounded">$&</mark>'
                              ),
                            }}
                          />
                        ) : (
                          result.sentenceText
                        )}
                      </p>

                      {/* Translation */}
                      {result.translation && (
                        <p className="text-gray-600 text-sm italic">{result.translation}</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex justify-center gap-2">
                <button
                  onClick={() => {
                    setPage(Math.max(1, page - 1));
                    performSearch();
                  }}
                  disabled={page === 1}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Previous
                </button>
                <span className="px-4 py-2 bg-white border border-gray-300 rounded-lg">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => {
                    setPage(Math.min(totalPages, page + 1));
                    performSearch();
                  }}
                  disabled={page === totalPages}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        ) : (
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
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <p className="text-gray-500 text-lg">Search for words or phrases</p>
            <p className="text-gray-400 text-sm mt-2">
              Find any word, phrase, or sentence across all videos
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
