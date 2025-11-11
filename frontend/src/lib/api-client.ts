/**
 * API Client for English Video Learning Platform
 * Axios-based client with JWT authentication, interceptors, and error handling
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

// ============================================
// Configuration
// ============================================

const API_BASE_URL = 'http://localhost:8000';
const TOKEN_KEY = 'auth_token';

// ============================================
// Type Definitions
// ============================================

export interface User {
  id: number;
  email?: string;
  name?: string;
  openId?: string;
  role: 'user' | 'admin';
  loginMethod?: string;
  createdAt: string;
  updatedAt?: string;
  lastSignedIn?: string;
}

export interface LoginRequest {
  email?: string;
  password?: string;
  open_id?: string;
}

export interface RegisterRequest {
  email: string;
  name: string;
  password?: string;
  open_id?: string;
  login_method?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Video {
  id: number;
  title: string;
  slug: string;
  description?: string;
  videoUrl: string;
  videoKey: string;
  thumbnailUrl?: string;
  duration?: number;
  level: 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2';
  language: string;
  categoryId?: number;
  uploadedBy: number;
  status: 'draft' | 'processing' | 'published' | 'archived';
  viewCount: number;
  createdAt: string;
  updatedAt?: string;
  publishedAt?: string;
  subtitles?: Subtitle[];
}

export interface Subtitle {
  id: number;
  videoId: number;
  language: string;
  languageName: string;
  subtitleUrl: string;
  subtitleKey: string;
  isDefault: number;
  source: 'manual' | 'ai_generated' | 'imported';
  createdAt: string;
  updatedAt?: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description?: string;
  createdAt: string;
}

export interface Vocabulary {
  id: number;
  userId: number;
  word: string;
  definition?: string;
  translation?: string;
  example?: string;
  videoId?: number;
  clipId?: number;
  timestamp?: number;
  mastery: 'learning' | 'familiar' | 'mastered';
  reviewCount: number;
  lastReviewed?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface Clip {
  id: number;
  videoId: number;
  userId: number;
  title: string;
  startTime: number;
  endTime: number;
  clipUrl?: string;
  clipKey?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  visibility: 'private' | 'public';
  createdAt: string;
  updatedAt?: string;
}

export interface SearchResult {
  videoId: number;
  videoTitle: string;
  videoSlug: string;
  thumbnailUrl?: string;
  sentenceId: number;
  sentenceText: string;
  translation?: string;
  timestamp: number;
  matchedPhrase?: string;
  level: string;
  relevanceScore: number;
}

export interface DashboardStats {
  totalVideos: number;
  totalUsers: number;
  totalClips: number;
  totalVocabulary: number;
  videosByStatus: {
    draft: number;
    processing: number;
    published: number;
    archived: number;
  };
  recentVideos: Video[];
  recentUsers: User[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface ApiError {
  detail: string;
  error?: string;
}

// ============================================
// Axios Instance with Interceptors
// ============================================

class ApiClient {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000, // 30 seconds
    });

    this.setupInterceptors();
  }

  /**
   * Setup request and response interceptors
   */
  private setupInterceptors(): void {
    // Request interceptor - Add JWT token to headers
    this.api.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = this.getToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error: AxiosError) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor - Handle errors globally
    this.api.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        // Handle 401 Unauthorized - Clear token and redirect to login
        if (error.response?.status === 401) {
          this.clearToken();
          // Optionally dispatch a logout event or redirect
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        }

        // Handle network errors
        if (!error.response) {
          console.error('Network error:', error.message);
          return Promise.reject({
            detail: 'Network error. Please check your connection.',
          });
        }

        // Return error details
        return Promise.reject(
          error.response?.data || { detail: 'An unexpected error occurred' }
        );
      }
    );
  }

  /**
   * Token Management
   */
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  }

  clearToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  }

  // ============================================
  // Authentication API
  // ============================================

  auth = {
    /**
     * Register a new user
     */
    register: async (data: RegisterRequest): Promise<TokenResponse> => {
      const response = await this.api.post<TokenResponse>('/api/auth/register', data);
      this.setToken(response.data.access_token);
      return response.data;
    },

    /**
     * Login user
     */
    login: async (data: LoginRequest): Promise<TokenResponse> => {
      const response = await this.api.post<TokenResponse>('/api/auth/login', data);
      this.setToken(response.data.access_token);
      return response.data;
    },

    /**
     * Logout user
     */
    logout: async (): Promise<void> => {
      await this.api.post('/api/auth/logout');
      this.clearToken();
    },

    /**
     * Get current user profile
     */
    me: async (): Promise<User> => {
      const response = await this.api.get<User>('/api/auth/me');
      return response.data;
    },

    /**
     * Check authentication status
     */
    check: async (): Promise<{ authenticated: boolean; user: User }> => {
      const response = await this.api.get('/api/auth/check');
      return response.data;
    },
  };

  // ============================================
  // Videos API
  // ============================================

  videos = {
    /**
     * List videos with pagination and filters
     */
    list: async (params?: {
      page?: number;
      pageSize?: number;
      category?: string;
      level?: string;
      status?: string;
      search?: string;
    }): Promise<PaginatedResponse<Video>> => {
      const response = await this.api.get<PaginatedResponse<Video>>('/api/videos', {
        params,
      });
      return response.data;
    },

    /**
     * Get video by ID
     */
    getById: async (videoId: number): Promise<Video> => {
      const response = await this.api.get<Video>(`/api/videos/${videoId}`);
      return response.data;
    },

    /**
     * Get video by slug
     */
    getBySlug: async (slug: string): Promise<Video> => {
      const response = await this.api.get<Video>(`/api/videos/slug/${slug}`);
      return response.data;
    },

    /**
     * Increment video view count
     */
    incrementView: async (videoId: number): Promise<{ viewCount: number }> => {
      const response = await this.api.post(`/api/videos/${videoId}/view`);
      return response.data;
    },
  };

  // ============================================
  // Admin API
  // ============================================

  admin = {
    /**
     * Get dashboard statistics
     */
    getDashboard: async (): Promise<DashboardStats> => {
      const response = await this.api.get<DashboardStats>('/api/admin/dashboard');
      return response.data;
    },

    /**
     * List videos (admin view)
     */
    listVideos: async (params?: {
      page?: number;
      pageSize?: number;
      status?: string;
      search?: string;
    }): Promise<PaginatedResponse<Video>> => {
      const response = await this.api.get<PaginatedResponse<Video>>('/api/admin/videos', {
        params,
      });
      return response.data;
    },

    /**
     * Create new video
     */
    createVideo: async (data: FormData): Promise<Video> => {
      const response = await this.api.post<Video>('/api/admin/videos', data, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    },

    /**
     * Update video
     */
    updateVideo: async (videoId: number, data: Partial<Video>): Promise<Video> => {
      const response = await this.api.put<Video>(`/api/admin/videos/${videoId}`, data);
      return response.data;
    },

    /**
     * Delete video
     */
    deleteVideo: async (videoId: number): Promise<void> => {
      await this.api.delete(`/api/admin/videos/${videoId}`);
    },

    /**
     * Trigger video processing pipeline
     */
    processVideo: async (
      videoId: number
    ): Promise<{ message: string; taskId: string }> => {
      const response = await this.api.post(`/api/admin/videos/${videoId}/process`);
      return response.data;
    },

    /**
     * Get video details (admin)
     */
    getVideo: async (videoId: number): Promise<Video> => {
      const response = await this.api.get<Video>(`/api/admin/videos/${videoId}`);
      return response.data;
    },
  };

  // ============================================
  // Vocabulary API
  // ============================================

  vocabulary = {
    /**
     * Save new vocabulary word
     */
    save: async (data: {
      word: string;
      definition?: string;
      translation?: string;
      example?: string;
      videoId?: number;
      clipId?: number;
      timestamp?: number;
    }): Promise<Vocabulary> => {
      const response = await this.api.post<Vocabulary>('/api/vocabulary/save', data);
      return response.data;
    },

    /**
     * List user's vocabulary
     */
    list: async (params?: {
      page?: number;
      pageSize?: number;
      mastery?: string;
      search?: string;
    }): Promise<PaginatedResponse<Vocabulary>> => {
      const response = await this.api.get<PaginatedResponse<Vocabulary>>(
        '/api/vocabulary',
        { params }
      );
      return response.data;
    },

    /**
     * Update vocabulary item
     */
    update: async (id: number, data: Partial<Vocabulary>): Promise<Vocabulary> => {
      const response = await this.api.patch<Vocabulary>(`/api/vocabulary/${id}`, data);
      return response.data;
    },

    /**
     * Delete vocabulary item
     */
    delete: async (id: number): Promise<void> => {
      await this.api.delete(`/api/vocabulary/${id}`);
    },

    /**
     * Get vocabulary statistics
     */
    getStats: async (): Promise<{
      total: number;
      byMastery: { learning: number; familiar: number; mastered: number };
      recentlyAdded: Vocabulary[];
    }> => {
      const response = await this.api.get('/api/vocabulary/stats');
      return response.data;
    },
  };

  // ============================================
  // Clips API
  // ============================================

  clips = {
    /**
     * Create a new clip
     */
    create: async (data: {
      videoId: number;
      title: string;
      startTime: number;
      endTime: number;
      visibility?: 'private' | 'public';
    }): Promise<Clip> => {
      const response = await this.api.post<Clip>('/api/clips/create', data);
      return response.data;
    },

    /**
     * List user's clips
     */
    list: async (params?: {
      page?: number;
      pageSize?: number;
      videoId?: number;
      status?: string;
    }): Promise<PaginatedResponse<Clip>> => {
      const response = await this.api.get<PaginatedResponse<Clip>>('/api/clips', {
        params,
      });
      return response.data;
    },

    /**
     * Get clip status
     */
    getStatus: async (id: number): Promise<Clip> => {
      const response = await this.api.get<Clip>(`/api/clips/${id}/status`);
      return response.data;
    },

    /**
     * Delete clip
     */
    delete: async (id: number): Promise<void> => {
      await this.api.delete(`/api/clips/${id}`);
    },

    /**
     * Get user's clip quota
     */
    getQuota: async (): Promise<{
      used: number;
      limit: number;
      remaining: number;
    }> => {
      const response = await this.api.get('/api/clips/quota');
      return response.data;
    },

    /**
     * Update clip visibility
     */
    updateVisibility: async (
      id: number,
      visibility: 'private' | 'public'
    ): Promise<Clip> => {
      const response = await this.api.patch<Clip>(`/api/clips/${id}/visibility`, {
        visibility,
      });
      return response.data;
    },
  };

  // ============================================
  // Search API
  // ============================================

  search = {
    /**
     * Search videos and subtitles
     */
    search: async (params: {
      query: string;
      page?: number;
      pageSize?: number;
      level?: string;
      videoId?: number;
    }): Promise<PaginatedResponse<SearchResult>> => {
      const response = await this.api.get<PaginatedResponse<SearchResult>>(
        '/api/search',
        { params }
      );
      return response.data;
    },

    /**
     * Get search suggestions
     */
    getSuggestions: async (query: string): Promise<string[]> => {
      const response = await this.api.get('/api/search/suggestions', {
        params: { query },
      });
      return response.data;
    },

    /**
     * Get phrase suggestions
     */
    getPhrases: async (query: string): Promise<string[]> => {
      const response = await this.api.get('/api/search/phrases', {
        params: { query },
      });
      return response.data;
    },

    /**
     * Get context around a sentence
     */
    getContext: async (
      sentenceId: number
    ): Promise<{ before: SearchResult[]; after: SearchResult[] }> => {
      const response = await this.api.get(`/api/search/context/${sentenceId}`);
      return response.data;
    },
  };

  // ============================================
  // Subtitles API
  // ============================================

  subtitles = {
    /**
     * List subtitles for a video
     */
    list: async (
      videoId: number
    ): Promise<{ videoId: number; subtitles: Subtitle[] }> => {
      const response = await this.api.get(`/api/subtitles/${videoId}`);
      return response.data;
    },

    /**
     * Get subtitle content (VTT format)
     */
    getContent: async (
      videoId: number,
      language: string
    ): Promise<{ content: string; language: string }> => {
      const response = await this.api.get(`/api/subtitles/${videoId}/content`, {
        params: { language },
      });
      return response.data;
    },

    /**
     * Download subtitle file
     */
    download: async (videoId: number, language: string): Promise<Blob> => {
      const response = await this.api.get(
        `/api/subtitles/${videoId}/download/${language}`,
        {
          responseType: 'blob',
        }
      );
      return response.data;
    },

    /**
     * Get sentences for editing (admin)
     */
    getSentences: async (
      videoId: number,
      params?: { language?: string; page?: number; pageSize?: number }
    ): Promise<
      Array<{
        id: number;
        text: string;
        translation?: string;
        startTime: number;
        endTime: number;
      }>
    > => {
      const response = await this.api.get(`/api/subtitles/admin/${videoId}/sentences`, {
        params,
      });
      return response.data;
    },

    /**
     * Update sentence (admin)
     */
    updateSentence: async (
      id: number,
      data: { text?: string; translation?: string }
    ): Promise<{
      id: number;
      text: string;
      translation?: string;
      startTime: number;
      endTime: number;
    }> => {
      const response = await this.api.patch(`/api/subtitles/admin/sentence/${id}`, data);
      return response.data;
    },

    /**
     * Delete sentence (admin)
     */
    deleteSentence: async (id: number): Promise<void> => {
      await this.api.delete(`/api/subtitles/admin/sentence/${id}`);
    },

    /**
     * Regenerate subtitles (admin)
     */
    regenerate: async (
      videoId: number,
      language: string
    ): Promise<{ message: string; taskId: string }> => {
      const response = await this.api.post(
        `/api/subtitles/admin/${videoId}/regenerate`,
        { language }
      );
      return response.data;
    },
  };
}

// ============================================
// Export Singleton Instance
// ============================================

const apiClient = new ApiClient();
export default apiClient;
