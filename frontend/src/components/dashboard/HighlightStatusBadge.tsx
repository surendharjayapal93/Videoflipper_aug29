import { AudioLines, CircleCheck, CircleX, Clock, Download, Scissors } from 'lucide-react';
import { Badge, type BadgeProps } from '@/components/ui/Badge';
import type { HighlightStatus } from '@/types';

const STATUS_CONFIG: Record<
  HighlightStatus,
  { label: string; variant: NonNullable<BadgeProps['variant']>; icon: typeof Clock }
> = {
  pending: { label: 'Pending', variant: 'secondary', icon: Clock },
  downloading: { label: 'Downloading', variant: 'info', icon: Download },
  analyzing: { label: 'Analyzing', variant: 'info', icon: AudioLines },
  rendering: { label: 'Rendering', variant: 'warning', icon: Scissors },
  completed: { label: 'Completed', variant: 'success', icon: CircleCheck },
  failed: { label: 'Failed', variant: 'destructive', icon: CircleX },
};

const SPINNING_STATUSES: ReadonlySet<HighlightStatus> = new Set([
  'downloading',
  'analyzing',
  'rendering',
]);

export interface HighlightStatusBadgeProps {
  status: HighlightStatus;
  className?: string;
}

/** Colored badge reflecting a Highlight job's processing status. */
export function HighlightStatusBadge({ status, className }: HighlightStatusBadgeProps) {
  const { label, variant, icon: Icon } = STATUS_CONFIG[status];

  return (
    <Badge variant={variant} className={className}>
      <Icon className={SPINNING_STATUSES.has(status) ? 'size-3.5 animate-spin' : 'size-3.5'} />
      {label}
    </Badge>
  );
}
