import { Clock, Download, Loader2, CircleCheck, CircleX } from 'lucide-react';
import { Badge, type BadgeProps } from '@/components/ui/Badge';
import type { VideoStatus } from '@/types';

const STATUS_CONFIG: Record<
  VideoStatus,
  { label: string; variant: NonNullable<BadgeProps['variant']>; icon: typeof Clock }
> = {
  pending: { label: 'Pending', variant: 'secondary', icon: Clock },
  downloading: { label: 'Downloading', variant: 'info', icon: Download },
  processing: { label: 'Processing', variant: 'warning', icon: Loader2 },
  completed: { label: 'Completed', variant: 'success', icon: CircleCheck },
  failed: { label: 'Failed', variant: 'destructive', icon: CircleX },
};

export interface StatusBadgeProps {
  status: VideoStatus;
  className?: string;
}

/** Colored badge that reflects a Video's processing status. */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  const { label, variant, icon: Icon } = STATUS_CONFIG[status];
  const isSpinning = status === 'processing' || status === 'downloading';

  return (
    <Badge variant={variant} className={className}>
      <Icon className={isSpinning ? 'size-3.5 animate-spin' : 'size-3.5'} />
      {label}
    </Badge>
  );
}
