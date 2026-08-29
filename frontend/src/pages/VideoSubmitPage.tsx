import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { FlipDirectionSelect } from '@/components/video/FlipDirectionSelect';
import { YoutubeUrlInput } from '@/components/video/YoutubeUrlInput';
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
import { getApiErrorMessage } from '@/lib/errors';
import { isValidYoutubeUrl } from '@/lib/youtube';
import { videoService } from '@/services/videoService';
import type { FlipDirection } from '@/types';

interface FormErrors {
  youtubeUrl?: string;
}

/** Form for submitting a new YouTube URL to be flipped. */
export function VideoSubmitPage() {
  const navigate = useNavigate();
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [flipDirection, setFlipDirection] = useState<FlipDirection>('horizontal');
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function validate(): boolean {
    const nextErrors: FormErrors = {};
    const trimmedUrl = youtubeUrl.trim();

    if (!trimmedUrl) {
      nextErrors.youtubeUrl = 'Please enter a YouTube URL.';
    } else if (!isValidYoutubeUrl(trimmedUrl)) {
      nextErrors.youtubeUrl = 'Please enter a valid YouTube video URL.';
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const video = await videoService.createVideo({
        youtubeUrl: youtubeUrl.trim(),
        flipDirection,
      });
      navigate(`/videos/${video.id}`);
    } catch (error) {
      setSubmitError(getApiErrorMessage(error, 'Failed to submit the video. Please try again.'));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <PageWrapper>
      <div className="mx-auto max-w-lg">
        <Card>
          <form onSubmit={(event) => void handleSubmit(event)} noValidate>
            <CardHeader>
              <CardTitle>Flip a new video</CardTitle>
              <CardDescription>Paste a YouTube URL and choose how to flip it.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <YoutubeUrlInput
                value={youtubeUrl}
                onChange={(event) => setYoutubeUrl(event.target.value)}
                error={errors.youtubeUrl}
                disabled={isSubmitting}
              />
              <FlipDirectionSelect
                value={flipDirection}
                onChange={setFlipDirection}
                disabled={isSubmitting}
              />
              {submitError && (
                <p role="alert" className="text-sm text-destructive">
                  {submitError}
                </p>
              )}
            </CardContent>
            <CardFooter>
              <Button type="submit" variant="gradient" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? 'Submitting...' : 'Flip video'}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </PageWrapper>
  );
}
