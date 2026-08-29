export interface User {
  id: number;
  email: string;
  fullName: string | null;
  isActive: boolean;
  isVerified: boolean;
  createdAt: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  fullName: string;
}

export interface UpdateProfileData {
  fullName: string;
}

export type FlipDirection = 'horizontal' | 'vertical' | 'both';

export type VideoStatus =
  | 'pending'
  | 'downloading'
  | 'processing'
  | 'completed'
  | 'failed';

export interface Video {
  id: number;
  youtubeUrl: string;
  sourceTitle: string | null;
  flipDirection: FlipDirection;
  status: VideoStatus;
  outputUrl: string | null;
  durationSeconds: number | null;
  fileSizeBytes: number | null;
  errorMessage: string | null;
  createdAt: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

export interface VideoSummary {
  id: number;
  sourceTitle: string | null;
  status: VideoStatus;
  createdAt: string;
}

export interface DashboardStats {
  totalVideos: number;
  completedVideos: number;
  failedVideos: number;
  processingVideos: number;
  totalStorageBytes: number;
  recentActivity: VideoSummary[];
}

export type HighlightStatus =
  | 'pending'
  | 'downloading'
  | 'analyzing'
  | 'rendering'
  | 'completed'
  | 'failed';

export interface Highlight {
  id: number;
  youtubeUrl: string;
  sourceTitle: string | null;
  status: HighlightStatus;
  sourceDurationSeconds: number | null;
  highlightDurationSeconds: number | null;
  fileSizeBytes: number | null;
  errorMessage: string | null;
  createdAt: string;
}
