import { Link } from 'react-router-dom';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { buttonVariants } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';

/** Landing page. Actual submission flow lands in a later phase. */
export function HomePage() {
  return (
    <PageWrapper>
      <div className="flex flex-col items-center gap-6 text-center">
        <h1 className="bg-gradient-to-r from-purple-600 to-pink-500 bg-clip-text text-4xl font-bold text-transparent sm:text-5xl">
          Flip any YouTube video
        </h1>
        <p className="max-w-xl text-muted-foreground">
          Paste a YouTube URL, choose a flip direction, and get a downloadable,
          flipped copy in minutes.
        </p>
        <Link to="/dashboard" className={buttonVariants({ variant: 'gradient', size: 'lg' })}>
          Get started
        </Link>

        <Card className="mt-8 w-full max-w-md text-left">
          <CardHeader>
            <CardTitle>How it works</CardTitle>
            <CardDescription>Three quick steps</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>1. Paste a YouTube link</p>
            <p>2. Pick horizontal, vertical, or both</p>
            <p>3. Download your flipped video</p>
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}
