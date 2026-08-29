import { isAxiosError } from 'axios';
import { CircleCheck, CircleX, HardDrive, Loader2, Video } from 'lucide-react';
import { useEffect, useState } from 'react';
import { HighlightGenerator } from '@/components/dashboard/HighlightGenerator';
import { RecentActivityList } from '@/components/dashboard/RecentActivityList';
import { StatCard } from '@/components/dashboard/StatCard';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { formatBytes } from '@/lib/utils';
import { getDashboardStats } from '@/services/dashboardService';
import type { ApiError, DashboardStats } from '@/types';

/** Authenticated landing page: usage stats + recent activity, aggregated from the user's videos. */
export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | undefined>(undefined);

  useEffect(() => {
    let isMounted = true;

    getDashboardStats()
      .then((data) => {
        if (isMounted) {
          setStats(data);
        }
      })
      .catch((fetchError: unknown) => {
        if (!isMounted) {
          return;
        }
        const message = isAxiosError<ApiError>(fetchError)
          ? (fetchError.response?.data?.error?.message ?? 'Unable to load dashboard stats.')
          : 'Unable to load dashboard stats.';
        setError(message);
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <PageWrapper>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            An overview of your video flipping activity.
          </p>
        </div>

        <HighlightGenerator />

        {isLoading && <p className="text-sm text-muted-foreground">Loading your stats...</p>}

        {error && !isLoading && <p className="text-sm text-destructive">{error}</p>}

        {stats && !isLoading && (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label="Total videos"
                value={stats.totalVideos}
                icon={<Video className="size-4" />}
              />
              <StatCard
                label="Completed"
                value={stats.completedVideos}
                icon={<CircleCheck className="size-4" />}
              />
              <StatCard
                label="Failed"
                value={stats.failedVideos}
                icon={<CircleX className="size-4" />}
              />
              <StatCard
                label="Processing"
                value={stats.processingVideos}
                icon={<Loader2 className="size-4" />}
              />
            </div>

            <StatCard
              label="Storage used"
              value={formatBytes(stats.totalStorageBytes)}
              icon={<HardDrive className="size-4" />}
              className="sm:max-w-xs"
            />

            <RecentActivityList videos={stats.recentActivity} />
          </>
        )}
      </div>
    </PageWrapper>
  );
}
