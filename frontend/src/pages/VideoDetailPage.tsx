import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { Button } from '@/components/ui/Button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { getApiErrorMessage } from '@/lib/errors';
import { triggerVideoDownload, videoService } from '@/services/videoService';
import type { Video, VideoStatus } from '@/types';

const ACTIVE_STATUSES: readonly VideoStatus[] = ['pending', 'downloading', 'processing'];
const POLL_INTERVAL_MS = 3000;

function formatFileSize(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Detail view for a single video: live status, metadata, download, and delete. */
export function VideoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const videoId = id ? Number(id) : NaN;

  const [video, setVideo] = useState<Video | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const isMountedRef = useRef(true);

  const fetchVideo = useCallback(
    async (showLoading: boolean) => {
      if (Number.isNaN(videoId)) {
        setLoadError('Invalid video id.');
        setIsLoading(false);
        return;
      }
      if (showLoading) setIsLoading(true);
      try {
        const data = await videoService.getVideo(videoId);
        if (isMountedRef.current) {
          setVideo(data);
          setLoadError(null);
        }
      } catch (error) {
        if (isMountedRef.current) {
          setLoadError(getApiErrorMessage(error, 'Failed to load this video.'));
        }
      } finally {
        if (isMountedRef.current && showLoading) setIsLoading(false);
      }
    },
    [videoId],
  );

  useEffect(() => {
    isMountedRef.current = true;
    void fetchVideo(true);
    return () => {
      isMountedRef.current = false;
    };
  }, [fetchVideo]);

  useEffect(() => {
    if (!video || !ACTIVE_STATUSES.includes(video.status)) return undefined;
    const timer = window.setInterval(() => void fetchVideo(false), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [video, fetchVideo]);

  async function handleDownload() {
    if (!video) return;
    setActionError(null);
    setIsDownloading(true);
    try {
      await triggerVideoDownload(video.id, video.sourceTitle ?? `video-${video.id}`);
    } catch (error) {
      setActionError(getApiErrorMessage(error, 'Failed to download the video.'));
    } finally {
      setIsDownloading(false);
    }
  }

  async function handleDelete() {
    if (!video) return;
    setActionError(null);
    setIsDeleting(true);
    try {
      await videoService.deleteVideo(video.id);
      navigate('/videos');
    } catch (error) {
      setActionError(getApiErrorMessage(error, 'Failed to delete the video.'));
      setIsDeleting(false);
    }
  }

  return (
    <PageWrapper>
      <div className="mx-auto max-w-2xl space-y-4">
        {isLoading && <p className="text-sm text-muted-foreground">Loading video...</p>}

        {loadError && (
          <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            {loadError}
          </div>
        )}

        {video && (
          <Card>
            <CardHeader className="flex-row items-start justify-between space-y-0">
              <div>
                <CardTitle>{video.sourceTitle ?? video.youtubeUrl}</CardTitle>
                <CardDescription>Flip: {video.flipDirection}</CardDescription>
              </div>
              <StatusBadge status={video.status} />
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>
                Source:{' '}
                <a
                  href={video.youtubeUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary hover:underline"
                >
                  {video.youtubeUrl}
                </a>
              </p>
              <p>Submitted: {new Date(video.createdAt).toLocaleString()}</p>
              {video.durationSeconds != null && <p>Duration: {video.durationSeconds}s</p>}
              {video.fileSizeBytes != null && <p>Size: {formatFileSize(video.fileSizeBytes)}</p>}
              {video.status === 'failed' && video.errorMessage && (
                <p className="text-destructive">{video.errorMessage}</p>
              )}
              {actionError && (
                <p role="alert" className="text-destructive">
                  {actionError}
                </p>
              )}
            </CardContent>
            <CardFooter className="gap-2">
              <Button
                type="button"
                variant="gradient"
                disabled={video.status !== 'completed' || isDownloading}
                onClick={() => void handleDownload()}
              >
                {isDownloading ? 'Downloading...' : 'Download'}
              </Button>
              <Button
                type="button"
                variant="destructive"
                disabled={isDeleting || ACTIVE_STATUSES.includes(video.status)}
                title={
                  ACTIVE_STATUSES.includes(video.status)
                    ? "Can't delete while still processing"
                    : undefined
                }
                onClick={() => void handleDelete()}
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </Button>
            </CardFooter>
          </Card>
        )}
      </div>
    </PageWrapper>
  );
}
