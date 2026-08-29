import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { VideoSummary } from '@/types';

export interface RecentActivityListProps {
  videos: VideoSummary[];
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/** Shows the most recently submitted videos and their current status. */
export function RecentActivityList({ videos }: RecentActivityListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent activity</CardTitle>
        <CardDescription>Your most recently submitted videos</CardDescription>
      </CardHeader>
      <CardContent>
        {videos.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No videos yet — submit one to get started.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {videos.map((video) => (
              <li
                key={video.id}
                className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {video.sourceTitle ?? `Video #${video.id}`}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatTimestamp(video.createdAt)}
                  </p>
                </div>
                <StatusBadge status={video.status} />
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
