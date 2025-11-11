'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '../../providers';
import apiClient, { Video, Subtitle } from '@/lib/api-client';

export default function VideoPlayerPage() {
  const params = useParams();
  const slug = params.slug as string;
  const { user } = useAuth();
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);

  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSubtitle, setSelectedSubtitle] = useState<string>('en');
  const [showVocabModal, setShowVocabModal] = useState(false);
  const [selectedWord, setSelectedWord] = useState('');
  const [savingWord, setSavingWord] = useState(false);

  useEffect(() => {
    if (slug) {
      fetchVideo();
    }
  }, [slug]);

  const fetchVideo = async () => {
    try {
      setLoading(true);
      const data = await apiClient.videos.getBySlug(slug);
      setVideo(data);

      // Increment view count
      await apiClient.videos.incrementView(data.id);
    } catch (error) {
      console.error('Failed to fetch video:', error);
      router.push('/');
    } finally {
      setLoading(false);
    }
  };

  const handleTextSelection = () => {
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    if (text && text.length > 0) {
      setSelectedWord(text);
      setShowVocabModal(true);
    }
  };

  const handleSaveWord = async () => {
    if (!user) {
      alert('Please login to save vocabulary');
      return;
    }

    try {
      setSavingWord(true);
      await apiClient.vocabulary.save({
        word: selectedWord,
        videoId: video?.id,
        timestamp: videoRef.current?.currentTime,
      });
      alert('Word saved to vocabulary!');
      setShowVocabModal(false);
    } catch (error) {
      console.error('Failed to save word:', error);
      alert('Failed to save word');
    } finally {
      setSavingWord(false);
    }
  };

  const handleCreateClip = async () => {
    if (!user) {
      alert('Please login to create clips');
      return;
    }

    const currentTime = videoRef.current?.currentTime || 0;
    const clipTitle = prompt('Enter clip title:');
    if (!clipTitle) return;

    try {
      await apiClient.clips.create({
        videoId: video!.id,
        title: clipTitle,
        startTime: Math.max(0, currentTime - 5),
        endTime: currentTime + 5,
      });
      alert('Clip created successfully!');
    } catch (error) {
      console.error('Failed to create clip:', error);
      alert('Failed to create clip');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
          <p className="mt-4 text-white">Loading video...</p>
        </div>
      </div>
    );
  }

  if (!video) {
    return null;
  }

  return (
    <div className="min-h-screen bg-black">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between">
            <a href="/" className="text-white hover:text-gray-300 text-sm">
              ← Back to Home
            </a>
            {user && (
              <div className="flex items-center gap-3">
                <a href="/vocabulary" className="text-white hover:text-gray-300 text-sm">
                  My Vocabulary
                </a>
                <a href="/my-clips" className="text-white hover:text-gray-300 text-sm">
                  My Clips
                </a>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Video Player */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-gray-900 rounded-lg overflow-hidden">
          <div className="relative aspect-video bg-black">
            <video
              ref={videoRef}
              controls
              className="w-full h-full"
              src={video.videoUrl}
              crossOrigin="anonymous"
            >
              {video.subtitles?.map((subtitle) => (
                <track
                  key={subtitle.id}
                  kind="subtitles"
                  src={subtitle.subtitleUrl}
                  srcLang={subtitle.language}
                  label={subtitle.languageName}
                  default={subtitle.isDefault === 1}
                />
              ))}
            </video>
          </div>

          {/* Video Info */}
          <div className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-2xl font-bold text-white mb-2">{video.title}</h1>
                <div className="flex items-center gap-4 text-sm text-gray-400">
                  <span className="px-2 py-1 bg-blue-600 text-white rounded">
                    {video.level}
                  </span>
                  <span>{video.viewCount} views</span>
                  {video.publishedAt && (
                    <span>{new Date(video.publishedAt).toLocaleDateString()}</span>
                  )}
                </div>
              </div>

              {user && (
                <button
                  onClick={handleCreateClip}
                  className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 text-sm"
                >
                  Create Clip
                </button>
              )}
            </div>

            {video.description && (
              <p className="text-gray-300 mb-4">{video.description}</p>
            )}

            {/* Subtitle Selection */}
            {video.subtitles && video.subtitles.length > 0 && (
              <div className="mt-4">
                <label className="block text-sm text-gray-400 mb-2">Subtitles:</label>
                <div className="flex flex-wrap gap-2">
                  {video.subtitles.map((subtitle) => (
                    <button
                      key={subtitle.id}
                      onClick={() => setSelectedSubtitle(subtitle.language)}
                      className={`px-3 py-1 rounded text-sm ${
                        selectedSubtitle === subtitle.language
                          ? 'bg-primary text-white'
                          : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                      }`}
                    >
                      {subtitle.languageName}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Interactive Transcript (Placeholder) */}
        {user && (
          <div className="mt-6 bg-gray-900 rounded-lg p-6">
            <h2 className="text-xl font-bold text-white mb-4">Interactive Transcript</h2>
            <div
              className="text-gray-300 leading-relaxed"
              onMouseUp={handleTextSelection}
            >
              <p className="mb-4">
                Select any word to save it to your vocabulary. The transcript will be
                synchronized with the video.
              </p>
              <p className="text-gray-500 italic">
                Transcript feature coming soon. You can still create clips and save vocabulary
                from the video.
              </p>
            </div>
          </div>
        )}

        {/* Vocabulary Modal */}
        {showVocabModal && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              <h3 className="text-lg font-bold mb-4">Save to Vocabulary</h3>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Word/Phrase
                </label>
                <input
                  type="text"
                  value={selectedWord}
                  onChange={(e) => setSelectedWord(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleSaveWord}
                  disabled={savingWord}
                  className="flex-1 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50"
                >
                  {savingWord ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={() => setShowVocabModal(false)}
                  className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
