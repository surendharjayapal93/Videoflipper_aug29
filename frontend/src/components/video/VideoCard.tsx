import { Link } from 'react-router-dom';
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
import type { Video } from '@/types';

const FLIP_DIRECTION_LABELS: Record<Video['flipDirection'], string> = {
  horizontal: 'Horizontal',
  vertical: 'Vertical',
  both: 'Both',
};

/** Statuses the backend still has an in-flight background job for — the
 * delete endpoint rejects deletion while a video is in one of these to
 * avoid orphaning files mid-pipeline (see backend `video_service.delete_video`). */
const ACTIVE_STATUSES: ReadonlySet<Video['status']> = new Set([
  'pending',
  'downloading',
  'processing',
]);

export interface VideoCardProps {
  video: Video;
  /** Omit to hide the download action (e.g. on the plain list page). */
  onDownload?: (id: number) => void;
  /** Omit to hide the delete action (e.g. on the plain list page). */
  onDelete?: (id: number) => void;
  isDownloading?: boolean;
  isDeleting?: boolean;
}

/** Card summarizing one video: title, status, flip direction, and optional inline actions. */
export function VideoCard({ video, onDownload, onDelete, isDownloading, isDeleting }: VideoCardProps) {
  const title = video.sourceTitle ?? video.youtubeUrl;

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <CardTitle className="truncate text-base" title={title}>
          <Link to={`/videos/${video.id}`} className="hover:underline">
            {title}
          </Link>
        </CardTitle>
        <StatusBadge status={video.status} />
      </CardHeader>
      <CardContent className="space-y-1">
        <CardDescription>Flip: {FLIP_DIRECTION_LABELS[video.flipDirection]}</CardDescription>
        <CardDescription>Submitted: {new Date(video.createdAt).toLocaleString()}</CardDescription>
        {video.status === 'failed' && video.errorMessage && (
          <p className="text-sm text-destructive">{video.errorMessage}</p>
        )}
      </CardContent>
      <CardFooter className="flex-wrap items-center gap-2">
        <Link to={`/videos/${video.id}`} className="text-sm font-medium text-primary hover:underline">
          View details
        </Link>
        {(onDownload || onDelete) && (
          <div className="ml-auto flex gap-2">
            {onDownload && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={video.status !== 'completed' || isDownloading}
                onClick={() => onDownload(video.id)}
              >
                {isDownloading ? 'Downloading...' : 'Download'}
              </Button>
            )}
            {onDelete && (
              <Button
                type="button"
                size="sm"
                variant="destructive"
                disabled={isDeleting || ACTIVE_STATUSES.has(video.status)}
                title={
                  ACTIVE_STATUSES.has(video.status)
                    ? "Can't delete while still processing"
                    : undefined
                }
                onClick={() => onDelete(video.id)}
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </Button>
            )}
          </div>
        )}
      </CardFooter>
    </Card>
  );
}
