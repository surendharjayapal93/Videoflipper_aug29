import api from '@/services/api';
import type { FlipDirection, Video, VideoStatus } from '@/types';

/** Wire-format shape returned by the API (snake_case per the backend contract). */
interface VideoDto {
  id: number;
  youtube_url: string;
  source_title: string | null;
  flip_direction: FlipDirection;
  status: VideoStatus;
  output_url: string | null;
  duration_seconds: number | null;
  file_size_bytes: number | null;
  error_message: string | null;
  created_at: string;
}

function fromDto(dto: VideoDto): Video {
  return {
    id: dto.id,
    youtubeUrl: dto.youtube_url,
    sourceTitle: dto.source_title,
    flipDirection: dto.flip_direction,
    status: dto.status,
    outputUrl: dto.output_url,
    durationSeconds: dto.duration_seconds,
    fileSizeBytes: dto.file_size_bytes,
    errorMessage: dto.error_message,
    createdAt: dto.created_at,
  };
}

export interface CreateVideoInput {
  youtubeUrl: string;
  flipDirection: FlipDirection;
}

export interface VideoListFilters {
  status?: VideoStatus;
  search?: string;
}

export const videoService = {
  /** POST /api/videos */
  async createVideo(input: CreateVideoInput): Promise<Video> {
    const { data } = await api.post<VideoDto>('/videos', {
      youtube_url: input.youtubeUrl,
      flip_direction: input.flipDirection,
    });
    return fromDto(data);
  },

  /** GET /api/videos?status=&search= */
  async listVideos(filters: VideoListFilters = {}): Promise<Video[]> {
    const params: Record<string, string> = {};
    if (filters.status) params.status = filters.status;
    if (filters.search) params.search = filters.search;

    const { data } = await api.get<VideoDto[]>('/videos', { params });
    return data.map(fromDto);
  },

  /** GET /api/videos/{id} */
  async getVideo(id: number): Promise<Video> {
    const { data } = await api.get<VideoDto>(`/videos/${id}`);
    return fromDto(data);
  },

  /** GET /api/videos/{id}/download — raw file stream as a Blob. */
  async downloadVideo(id: number): Promise<Blob> {
    const { data } = await api.get<Blob>(`/videos/${id}/download`, {
      responseType: 'blob',
    });
    return data;
  },

  /** DELETE /api/videos/{id} */
  async deleteVideo(id: number): Promise<void> {
    await api.delete(`/videos/${id}`);
  },
};

function sanitizeFilename(name: string): string {
  const cleaned = name.replace(/[\\/:*?"<>|]+/g, '_').trim();
  const base = cleaned || 'video';
  return base.toLowerCase().endsWith('.mp4') ? base : `${base}.mp4`;
}

/**
 * Downloads the flipped video and saves it to disk via a synthetic anchor
 * click, since the backend serves it as a raw file stream rather than a URL.
 */
export async function triggerVideoDownload(id: number, filenameHint: string): Promise<void> {
  const blob = await videoService.downloadVideo(id);
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = sanitizeFilename(filenameHint);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
}
