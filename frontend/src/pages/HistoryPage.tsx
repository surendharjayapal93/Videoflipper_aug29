import { useState } from 'react';
import { VideoCard } from '@/components/video/VideoCard';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useVideos } from '@/hooks/useVideos';
import { getApiErrorMessage } from '@/lib/errors';
import { triggerVideoDownload, videoService } from '@/services/videoService';
import type { VideoStatus } from '@/types';

type StatusFilter = VideoStatus | 'all';

const STATUS_OPTIONS: Array<{ value: StatusFilter; label: string }> = [
  { value: 'all', label: 'All statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'downloading', label: 'Downloading' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
];

/** Searchable, filterable view over the full video history with inline actions. */
export function HistoryPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [search, setSearch] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingDownloadId, setPendingDownloadId] = useState<number | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

  const { videos, isLoading, error, refetch, removeVideo } = useVideos({
    status: statusFilter === 'all' ? undefined : statusFilter,
    search: search.trim() || undefined,
  });

  async function handleDownload(id: number) {
    setActionError(null);
    setPendingDownloadId(id);
    try {
      const video = videos.find((item) => item.id === id);
      await triggerVideoDownload(id, video?.sourceTitle ?? `video-${id}`);
    } catch (error) {
      setActionError(getApiErrorMessage(error, 'Failed to download the video.'));
    } finally {
      setPendingDownloadId(null);
    }
  }

  async function handleDelete(id: number) {
    setActionError(null);
    setPendingDeleteId(id);
    try {
      await videoService.deleteVideo(id);
      removeVideo(id);
    } catch (error) {
      setActionError(getApiErrorMessage(error, 'Failed to delete the video.'));
    } finally {
      setPendingDeleteId(null);
    }
  }

  return (
    <PageWrapper>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">History</h1>
          <p className="text-sm text-muted-foreground">
            Search and filter everything you have submitted.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Input
            placeholder="Search by title or URL..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="sm:max-w-xs"
            aria-label="Search history"
          />
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            aria-label="Filter by status"
            className="flex h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:max-w-xs"
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {(error || actionError) && (
          <div className="flex items-center justify-between rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            <span>{error ?? actionError}</span>
            {error && (
              <Button type="button" variant="outline" size="sm" onClick={() => void refetch()}>
                Retry
              </Button>
            )}
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading history...</p>
        ) : videos.length === 0 ? (
          <p className="text-sm text-muted-foreground">No videos match your filters.</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {videos.map((video) => (
              <VideoCard
                key={video.id}
                video={video}
                onDownload={(id) => void handleDownload(id)}
                onDelete={(id) => void handleDelete(id)}
                isDownloading={pendingDownloadId === video.id}
                isDeleting={pendingDeleteId === video.id}
              />
            ))}
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
