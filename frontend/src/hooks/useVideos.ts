import { useCallback, useEffect, useRef, useState } from 'react';
import { getApiErrorMessage } from '@/lib/errors';
import { videoService } from '@/services/videoService';
import type { Video, VideoStatus } from '@/types';

const ACTIVE_STATUSES: readonly VideoStatus[] = ['pending', 'downloading', 'processing'];
const DEFAULT_POLL_INTERVAL_MS = 3000;

export interface UseVideosOptions {
  status?: VideoStatus;
  search?: string;
  pollIntervalMs?: number;
}

export interface UseVideosResult {
  videos: Video[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  /** Optimistically drops a video from local state (e.g. right after a delete). */
  removeVideo: (id: number) => void;
}

/**
 * Fetches the video list for the given filters and polls in the background
 * (every `pollIntervalMs`, default 3s) as long as at least one video is
 * still pending/downloading/processing, so statuses update without a
 * manual refresh.
 */
export function useVideos(options: UseVideosOptions = {}): UseVideosResult {
  const { status, search, pollIntervalMs = DEFAULT_POLL_INTERVAL_MS } = options;

  const [videos, setVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const isMountedRef = useRef(true);
  const videosRef = useRef<Video[]>([]);

  useEffect(() => {
    videosRef.current = videos;
  }, [videos]);

  const fetchVideos = useCallback(
    async (showLoading: boolean) => {
      if (showLoading) setIsLoading(true);
      try {
        const data = await videoService.listVideos({ status, search });
        if (isMountedRef.current) {
          setVideos(data);
          setError(null);
        }
      } catch (err) {
        if (isMountedRef.current) {
          setError(getApiErrorMessage(err, 'Failed to load videos.'));
        }
      } finally {
        if (isMountedRef.current && showLoading) setIsLoading(false);
      }
    },
    [status, search],
  );

  useEffect(() => {
    isMountedRef.current = true;
    void fetchVideos(true);
    return () => {
      isMountedRef.current = false;
    };
  }, [fetchVideos]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      const hasActiveVideo = videosRef.current.some((video) =>
        ACTIVE_STATUSES.includes(video.status),
      );
      if (hasActiveVideo) void fetchVideos(false);
    }, pollIntervalMs);

    return () => window.clearInterval(timer);
  }, [fetchVideos, pollIntervalMs]);

  const removeVideo = useCallback((id: number) => {
    setVideos((prev) => prev.filter((video) => video.id !== id));
  }, []);

  return {
    videos,
    isLoading,
    error,
    refetch: () => fetchVideos(true),
    removeVideo,
  };
}
