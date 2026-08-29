import api from '@/services/api';
import type { Highlight, HighlightStatus } from '@/types';

/** Wire-format shape returned by the API (snake_case per the backend contract). */
interface HighlightDto {
  id: number;
  youtube_url: string;
  source_title: string | null;
  status: HighlightStatus;
  source_duration_seconds: number | null;
  highlight_duration_seconds: number | null;
  file_size_bytes: number | null;
  error_message: string | null;
  created_at: string;
}

function fromDto(dto: HighlightDto): Highlight {
  return {
    id: dto.id,
    youtubeUrl: dto.youtube_url,
    sourceTitle: dto.source_title,
    status: dto.status,
    sourceDurationSeconds: dto.source_duration_seconds,
    highlightDurationSeconds: dto.highlight_duration_seconds,
    fileSizeBytes: dto.file_size_bytes,
    errorMessage: dto.error_message,
    createdAt: dto.created_at,
  };
}

export const highlightService = {
  /** POST /highlights */
  async createHighlight(youtubeUrl: string): Promise<Highlight> {
    const { data } = await api.post<HighlightDto>('/highlights', { youtube_url: youtubeUrl });
    return fromDto(data);
  },

  /** GET /highlights/{id} */
  async getHighlight(id: number): Promise<Highlight> {
    const { data } = await api.get<HighlightDto>(`/highlights/${id}`);
    return fromDto(data);
  },

  /** GET /highlights/{id}/download — raw file stream as a Blob. */
  async downloadHighlight(id: number): Promise<Blob> {
    const { data } = await api.get<Blob>(`/highlights/${id}/download`, {
      responseType: 'blob',
    });
    return data;
  },
};

function sanitizeFilename(name: string): string {
  const cleaned = name.replace(/[\\/:*?"<>|]+/g, '_').trim();
  const base = cleaned || 'highlight';
  return base.toLowerCase().endsWith('.mp4') ? base : `${base}.mp4`;
}

/**
 * Downloads the highlight reel and saves it to disk via a synthetic anchor
 * click, since the backend serves it as a raw file stream rather than a URL.
 */
export async function triggerHighlightDownload(id: number, filenameHint: string): Promise<void> {
  const blob = await highlightService.downloadHighlight(id);
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = sanitizeFilename(filenameHint);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
}
