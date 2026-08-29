import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ComponentProps } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { VideoCard } from '@/components/video/VideoCard';
import type { Video } from '@/types';

function makeVideo(overrides: Partial<Video> = {}): Video {
  return {
    id: 1,
    youtubeUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    sourceTitle: 'My Flipped Video',
    flipDirection: 'horizontal',
    status: 'completed',
    outputUrl: null,
    durationSeconds: 30,
    fileSizeBytes: 1024,
    errorMessage: null,
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function renderCard(props: Partial<ComponentProps<typeof VideoCard>> = {}) {
  const video = props.video ?? makeVideo();
  return render(
    <MemoryRouter>
      <VideoCard video={video} {...props} />
    </MemoryRouter>,
  );
}

describe('VideoCard', () => {
  it('renders the source title, status badge, and flip direction', () => {
    renderCard();

    expect(screen.getByText('My Flipped Video')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Flip: Horizontal')).toBeInTheDocument();
  });

  it('falls back to the raw YouTube URL when there is no source title', () => {
    renderCard({ video: makeVideo({ sourceTitle: null }) });

    expect(
      screen.getByRole('link', { name: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' }),
    ).toBeInTheDocument();
  });

  it('shows the error message for a failed video', () => {
    renderCard({
      video: makeVideo({ status: 'failed', errorMessage: 'Download failed: 404' }),
    });

    expect(screen.getByText('Download failed: 404')).toBeInTheDocument();
  });

  it('does not render action buttons when no handlers are provided', () => {
    renderCard();

    expect(screen.queryByRole('button', { name: /download/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
  });

  it('calls onDownload with the video id when Download is clicked', async () => {
    const user = userEvent.setup();
    const onDownload = vi.fn();
    renderCard({ onDownload });

    await user.click(screen.getByRole('button', { name: 'Download' }));

    expect(onDownload).toHaveBeenCalledWith(1);
  });

  it('disables Download when the video is not completed', () => {
    const onDownload = vi.fn();
    renderCard({ video: makeVideo({ status: 'processing' }), onDownload });

    expect(screen.getByRole('button', { name: 'Download' })).toBeDisabled();
  });

  it('calls onDelete with the video id when Delete is clicked', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    renderCard({ onDelete });

    await user.click(screen.getByRole('button', { name: 'Delete' }));

    expect(onDelete).toHaveBeenCalledWith(1);
  });
});
