import { api } from '@/services/api';
import type { DashboardStats, VideoStatus, VideoSummary } from '@/types';

/** Raw shape returned by the backend (snake_case) before mapping to app types. */
interface VideoSummaryResponse {
  id: number;
  source_title: string | null;
  status: VideoStatus;
  created_at: string;
}

interface DashboardStatsResponse {
  total_videos: number;
  completed_videos: number;
  failed_videos: number;
  processing_videos: number;
  total_storage_bytes: number;
  recent_activity: VideoSummaryResponse[];
}

function mapVideoSummary(data: VideoSummaryResponse): VideoSummary {
  return {
    id: data.id,
    sourceTitle: data.source_title,
    status: data.status,
    createdAt: data.created_at,
  };
}

function mapDashboardStats(data: DashboardStatsResponse): DashboardStats {
  return {
    totalVideos: data.total_videos,
    completedVideos: data.completed_videos,
    failedVideos: data.failed_videos,
    processingVideos: data.processing_videos,
    totalStorageBytes: data.total_storage_bytes,
    recentActivity: data.recent_activity.map(mapVideoSummary),
  };
}

/** Fetch aggregated usage stats + recent activity for the current user. */
export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStatsResponse>('/dashboard/stats');
  return mapDashboardStats(data);
}
