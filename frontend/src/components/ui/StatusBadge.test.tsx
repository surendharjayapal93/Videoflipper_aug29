import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { VideoStatus } from '@/types';

describe('StatusBadge', () => {
  it.each<[VideoStatus, string, string]>([
    ['pending', 'Pending', 'bg-secondary'],
    ['downloading', 'Downloading', 'bg-info'],
    ['processing', 'Processing', 'bg-warning'],
    ['completed', 'Completed', 'bg-success'],
    ['failed', 'Failed', 'bg-destructive'],
  ])('renders the %s status with label %s and variant class %s', (status, label, variantClass) => {
    render(<StatusBadge status={status} />);

    const badge = screen.getByText(label).closest('span');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass(variantClass);
  });

  it('spins the icon for in-progress statuses (downloading, processing)', () => {
    const { rerender } = render(<StatusBadge status="downloading" />);
    expect(screen.getByText('Downloading').parentElement?.querySelector('svg')).toHaveClass(
      'animate-spin',
    );

    rerender(<StatusBadge status="processing" />);
    expect(screen.getByText('Processing').parentElement?.querySelector('svg')).toHaveClass(
      'animate-spin',
    );
  });

  it('does not spin the icon for terminal statuses (completed, failed, pending)', () => {
    const { rerender } = render(<StatusBadge status="completed" />);
    expect(screen.getByText('Completed').parentElement?.querySelector('svg')).not.toHaveClass(
      'animate-spin',
    );

    rerender(<StatusBadge status="failed" />);
    expect(screen.getByText('Failed').parentElement?.querySelector('svg')).not.toHaveClass(
      'animate-spin',
    );

    rerender(<StatusBadge status="pending" />);
    expect(screen.getByText('Pending').parentElement?.querySelector('svg')).not.toHaveClass(
      'animate-spin',
    );
  });
});
