import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HighlightGenerator } from '@/components/dashboard/HighlightGenerator';
import { renderWithProviders } from '@/test/utils';
import type { Highlight } from '@/types';

vi.mock('@/services/highlightService', () => ({
  highlightService: {
    createHighlight: vi.fn(),
    getHighlight: vi.fn(),
    downloadHighlight: vi.fn(),
  },
  triggerHighlightDownload: vi.fn(),
}));

import { highlightService, triggerHighlightDownload } from '@/services/highlightService';

const mockedCreateHighlight = vi.mocked(highlightService.createHighlight);
const mockedTriggerDownload = vi.mocked(triggerHighlightDownload);

const VALID_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';

function makeHighlight(overrides: Partial<Highlight> = {}): Highlight {
  return {
    id: 7,
    youtubeUrl: VALID_URL,
    sourceTitle: null,
    status: 'pending',
    sourceDurationSeconds: null,
    highlightDurationSeconds: null,
    fileSizeBytes: null,
    errorMessage: null,
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('HighlightGenerator', () => {
  beforeEach(() => {
    mockedCreateHighlight.mockReset();
    mockedTriggerDownload.mockReset();
  });

  it('shows a validation error when the URL is empty', async () => {
    const user = userEvent.setup();
    renderWithProviders(<HighlightGenerator />);

    await user.click(screen.getByRole('button', { name: /generate highlights/i }));

    expect(await screen.findByText('Please enter a YouTube URL.')).toBeInTheDocument();
    expect(mockedCreateHighlight).not.toHaveBeenCalled();
  });

  it('shows a validation error for a non-YouTube URL', async () => {
    const user = userEvent.setup();
    renderWithProviders(<HighlightGenerator />);

    await user.type(screen.getByLabelText(/youtube url/i), 'https://vimeo.com/12345');
    await user.click(screen.getByRole('button', { name: /generate highlights/i }));

    expect(
      await screen.findByText('Please enter a valid YouTube video URL.'),
    ).toBeInTheDocument();
    expect(mockedCreateHighlight).not.toHaveBeenCalled();
  });

  it('submits the URL and shows the resulting status', async () => {
    mockedCreateHighlight.mockResolvedValue(makeHighlight({ status: 'pending' }));
    const user = userEvent.setup();
    renderWithProviders(<HighlightGenerator />);

    await user.type(screen.getByLabelText(/youtube url/i), VALID_URL);
    await user.click(screen.getByRole('button', { name: /generate highlights/i }));

    await waitFor(() => {
      expect(mockedCreateHighlight).toHaveBeenCalledWith(VALID_URL);
    });
    expect(await screen.findByText('Pending')).toBeInTheDocument();
  });

  it('shows an error message when submission fails', async () => {
    mockedCreateHighlight.mockRejectedValue(new Error('Network error'));
    const user = userEvent.setup();
    renderWithProviders(<HighlightGenerator />);

    await user.type(screen.getByLabelText(/youtube url/i), VALID_URL);
    await user.click(screen.getByRole('button', { name: /generate highlights/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Network error');
  });

  it('shows a download button once completed and triggers the download', async () => {
    mockedCreateHighlight.mockResolvedValue(
      makeHighlight({
        status: 'completed',
        sourceTitle: 'Test Video',
        highlightDurationSeconds: 60,
        sourceDurationSeconds: 300,
      }),
    );
    mockedTriggerDownload.mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderWithProviders(<HighlightGenerator />);

    await user.type(screen.getByLabelText(/youtube url/i), VALID_URL);
    await user.click(screen.getByRole('button', { name: /generate highlights/i }));

    const downloadButton = await screen.findByRole('button', { name: /download highlight/i });
    await user.click(downloadButton);

    await waitFor(() => {
      expect(mockedTriggerDownload).toHaveBeenCalledWith(7, 'Test Video');
    });
  });

  it('resets the form when "Generate another" is clicked', async () => {
    mockedCreateHighlight.mockResolvedValue(makeHighlight({ status: 'completed' }));
    const user = userEvent.setup();
    renderWithProviders(<HighlightGenerator />);

    await user.type(screen.getByLabelText(/youtube url/i), VALID_URL);
    await user.click(screen.getByRole('button', { name: /generate highlights/i }));

    await screen.findByRole('button', { name: /generate another/i });
    await user.click(screen.getByRole('button', { name: /generate another/i }));

    expect(screen.getByLabelText(/youtube url/i)).toHaveValue('');
  });
});
