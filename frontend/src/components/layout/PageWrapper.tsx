import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface PageWrapperProps {
  children: ReactNode;
  className?: string;
}

/**
 * Wraps every route's content: full-height container, consistent max-width
 * gutter, and a subtle fade/slide-in transition on mount.
 */
export function PageWrapper({ children, className }: PageWrapperProps) {
  return (
    <div
      className={cn(
        'min-h-screen w-full animate-fade-in',
        className,
      )}
    >
      <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">{children}</div>
    </div>
  );
}
