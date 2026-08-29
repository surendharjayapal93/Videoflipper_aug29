import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { HighlightStatusBadge } from '@/components/dashboard/HighlightStatusBadge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { YoutubeUrlInput } from '@/components/video/YoutubeUrlInput';
import { getApiErrorMessage } from '@/lib/errors';
import { isValidYoutubeUrl } from '@/lib/youtube';
import { highlightService, triggerHighlightDownload } from '@/services/highlightService';
import type { Highlight, HighlightStatus } from '@/types';

const ACTIVE_STATUSES: readonly HighlightStatus[] = [
  'pending',
  'downloading',
  'analyzing',
  'rendering',
];
const POLL_INTERVAL_MS = 3000;

function formatDuration(seconds: number): string {
  const rounded = Math.round(seconds);
  const m = Math.floor(rounded / 60);
  const s = rounded % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

/**
 * Dashboard widget: paste a YouTube URL, generate a ~1 minute highlight
 * reel (audio-activity-based content selection), and download it once ready.
 */
export function HighlightGenerator() {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [urlError, setUrlError] = useState<string | undefined>(undefined);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [highlight, setHighlight] = useState<Highlight | null>(null);

  const isMountedRef = useRef(true);
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const pollHighlight = useCallback(async (id: number) => {
    try {
      const data = await highlightService.getHighlight(id);
      if (isMountedRef.current) {
        setHighlight(data);
      }
    } catch (error) {
      if (isMountedRef.current) {
        setSubmitError(getApiErrorMessage(error, 'Failed to check highlight status.'));
      }
    }
  }, []);

  useEffect(() => {
    if (!highlight || !ACTIVE_STATUSES.includes(highlight.status)) return undefined;
    const timer = window.setInterval(() => void pollHighlight(highlight.id), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [highlight, pollHighlight]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    const trimmedUrl = youtubeUrl.trim();
    if (!trimmedUrl) {
      setUrlError('Please enter a YouTube URL.');
      return;
    }
    if (!isValidYoutubeUrl(trimmedUrl)) {
      setUrlError('Please enter a valid YouTube video URL.');
      return;
    }
    setUrlError(undefined);

    setIsSubmitting(true);
    try {
      const created = await highlightService.createHighlight(trimmedUrl);
      setHighlight(created);
    } catch (error) {
      setSubmitError(getApiErrorMessage(error, 'Failed to submit the video. Please try again.'));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDownload() {
    if (!highlight) return;
    setSubmitError(null);
    setIsDownloading(true);
    try {
      await triggerHighlightDownload(
        highlight.id,
        highlight.sourceTitle ?? `highlight-${highlight.id}`,
      );
    } catch (error) {
      setSubmitError(getApiErrorMessage(error, 'Failed to download the highlight reel.'));
    } finally {
      setIsDownloading(false);
    }
  }

  function handleGenerateAnother() {
    setHighlight(null);
    setYoutubeUrl('');
    setSubmitError(null);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generate a 1-minute highlight reel</CardTitle>
        <CardDescription>
          Paste a YouTube URL — we&apos;ll download it and automatically cut together the most
          active ~60 seconds (based on audio activity) into one highlight clip.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!highlight ? (
          <form onSubmit={(event) => void handleSubmit(event)} noValidate className="space-y-4">
            <YoutubeUrlInput
              value={youtubeUrl}
              onChange={(event) => setYoutubeUrl(event.target.value)}
              error={urlError}
              disabled={isSubmitting}
            />
            {submitError && (
              <p role="alert" className="text-sm text-destructive">
                {submitError}
              </p>
            )}
            <Button type="submit" variant="gradient" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting...' : 'Generate highlights'}
            </Button>
          </form>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">
                {highlight.sourceTitle ?? highlight.youtubeUrl}
              </span>
              <HighlightStatusBadge status={highlight.status} />
            </div>

            {highlight.status === 'failed' && highlight.errorMessage && (
              <p className="text-sm text-destructive">{highlight.errorMessage}</p>
            )}

            {highlight.status === 'completed' && highlight.highlightDurationSeconds != null && (
              <p className="text-sm text-muted-foreground">
                Highlight length: {formatDuration(highlight.highlightDurationSeconds)}
                {highlight.sourceDurationSeconds != null &&
                  ` (from a ${formatDuration(highlight.sourceDurationSeconds)} source)`}
              </p>
            )}

            {submitError && (
              <p role="alert" className="text-sm text-destructive">
                {submitError}
              </p>
            )}

            <div className="flex flex-wrap gap-2">
              {highlight.status === 'completed' && (
                <Button
                  type="button"
                  variant="gradient"
                  disabled={isDownloading}
                  onClick={() => void handleDownload()}
                >
                  {isDownloading ? 'Downloading...' : 'Download highlight'}
                </Button>
              )}
              <Button type="button" variant="outline" onClick={handleGenerateAnother}>
                Generate another
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
