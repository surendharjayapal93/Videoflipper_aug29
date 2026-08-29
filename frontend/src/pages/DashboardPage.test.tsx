import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardPage } from '@/pages/DashboardPage';
import { renderWithProviders } from '@/test/utils';
import type { DashboardStats } from '@/types';

vi.mock('@/services/dashboardService', () => ({
  getDashboardStats: vi.fn(),
}));

import { getDashboardStats } from '@/services/dashboardService';

const mockedGetDashboardStats = vi.mocked(getDashboardStats);

const STATS: DashboardStats = {
  totalVideos: 5,
  completedVideos: 3,
  failedVideos: 1,
  processingVideos: 1,
  totalStorageBytes: 1024 * 1024,
  recentActivity: [
    { id: 1, sourceTitle: 'First video', status: 'completed', createdAt: '2026-01-02T00:00:00Z' },
    { id: 2, sourceTitle: null, status: 'failed', createdAt: '2026-01-01T00:00:00Z' },
  ],
};

describe('DashboardPage', () => {
  beforeEach(() => {
    mockedGetDashboardStats.mockReset();
  });

  it('renders aggregated stats and recent activity once loaded', async () => {
    mockedGetDashboardStats.mockResolvedValue(STATS);
    renderWithProviders(<DashboardPage />);

    expect(screen.getByText('Loading your stats...')).toBeInTheDocument();

    expect(await screen.findByText('First video')).toBeInTheDocument();
    expect(screen.getByText('Total videos')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Video #2')).toBeInTheDocument();
    expect(screen.queryByText('Loading your stats...')).not.toBeInTheDocument();
  });

  it('shows a fallback error message when the stats request fails', async () => {
    mockedGetDashboardStats.mockRejectedValue(new Error('boom'));
    renderWithProviders(<DashboardPage />);

    // DashboardPage only surfaces the backend's `error.message` for Axios
    // errors; any other thrown error falls back to a generic message.
    expect(await screen.findByText('Unable to load dashboard stats.')).toBeInTheDocument();
  });
});
