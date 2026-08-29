import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { VideoSubmitPage } from '@/pages/VideoSubmitPage';
import { renderWithProviders } from '@/test/utils';
import type { Video } from '@/types';

vi.mock('@/services/videoService', () => ({
  videoService: {
    createVideo: vi.fn(),
    listVideos: vi.fn(),
    getVideo: vi.fn(),
    downloadVideo: vi.fn(),
    deleteVideo: vi.fn(),
  },
  triggerVideoDownload: vi.fn(),
}));

import { videoService } from '@/services/videoService';

const mockedCreateVideo = vi.mocked(videoService.createVideo);

const VALID_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';

function renderSubmitPage() {
  return renderWithProviders(<VideoSubmitPage />, {
    route: '/submit',
    path: '/submit',
    extraRoutes: <Route path="/videos/:id" element={<p>Video detail page</p>} />,
  });
}

function makeVideo(overrides: Partial<Video> = {}): Video {
  return {
    id: 42,
    youtubeUrl: VALID_URL,
    sourceTitle: null,
    flipDirection: 'horizontal',
    status: 'pending',
    outputUrl: null,
    durationSeconds: null,
    fileSizeBytes: null,
    errorMessage: null,
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('VideoSubmitPage', () => {
  beforeEach(() => {
    mockedCreateVideo.mockReset();
  });

  it('shows a validation error when the URL is empty', async () => {
    const user = userEvent.setup();
    renderSubmitPage();

    await user.click(screen.getByRole('button', { name: /flip video/i }));

    expect(await screen.findByText('Please enter a YouTube URL.')).toBeInTheDocument();
    expect(mockedCreateVideo).not.toHaveBeenCalled();
  });

  it('shows a validation error for a non-YouTube URL', async () => {
    const user = userEvent.setup();
    renderSubmitPage();

    await user.type(screen.getByLabelText(/youtube url/i), 'https://vimeo.com/12345');
    await user.click(screen.getByRole('button', { name: /flip video/i }));

    expect(
      await screen.findByText('Please enter a valid YouTube video URL.'),
    ).toBeInTheDocument();
    expect(mockedCreateVideo).not.toHaveBeenCalled();
  });

  it('submits the URL and chosen flip direction, then navigates to the video detail page', async () => {
    mockedCreateVideo.mockResolvedValue(makeVideo({ id: 42 }));
    const user = userEvent.setup();
    renderSubmitPage();

    await user.type(screen.getByLabelText(/youtube url/i), VALID_URL);
    await user.selectOptions(screen.getByLabelText(/flip direction/i), 'vertical');
    await user.click(screen.getByRole('button', { name: /flip video/i }));

    await waitFor(() => {
      expect(mockedCreateVideo).toHaveBeenCalledWith({
        youtubeUrl: VALID_URL,
        flipDirection: 'vertical',
      });
    });
    expect(await screen.findByText('Video detail page')).toBeInTheDocument();
  });

  it('shows an error message when submission fails', async () => {
    mockedCreateVideo.mockRejectedValue(new Error('Network error'));
    const user = userEvent.setup();
    renderSubmitPage();

    await user.type(screen.getByLabelText(/youtube url/i), VALID_URL);
    await user.click(screen.getByRole('button', { name: /flip video/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Network error');
  });
});
