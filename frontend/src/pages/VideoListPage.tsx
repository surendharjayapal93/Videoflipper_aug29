import { Link } from 'react-router-dom';
import { VideoCard } from '@/components/video/VideoCard';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { Button, buttonVariants } from '@/components/ui/Button';
import { useVideos } from '@/hooks/useVideos';

/** Grid of all submitted videos with a link to submit a new one. */
export function VideoListPage() {
  const { videos, isLoading, error, refetch } = useVideos();

  return (
    <PageWrapper>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">Your videos</h1>
            <p className="text-sm text-muted-foreground">
              Videos you have submitted for flipping.
            </p>
          </div>
          <Link to="/videos/new" className={buttonVariants({ variant: 'gradient' })}>
            Flip a new video
          </Link>
        </div>

        {error && (
          <div className="flex items-center justify-between rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            <span>{error}</span>
            <Button type="button" variant="outline" size="sm" onClick={() => void refetch()}>
              Retry
            </Button>
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading videos...</p>
        ) : videos.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No videos yet.{' '}
            <Link to="/videos/new" className="text-primary hover:underline">
              Submit your first one.
            </Link>
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {videos.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
