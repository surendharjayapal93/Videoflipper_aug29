import { type SelectHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import type { FlipDirection } from '@/types';

export interface FlipDirectionSelectProps
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'value' | 'onChange'> {
  value: FlipDirection;
  onChange: (value: FlipDirection) => void;
  label?: string;
  error?: string;
}

const FLIP_DIRECTION_OPTIONS: Array<{ value: FlipDirection; label: string }> = [
  { value: 'horizontal', label: 'Horizontal' },
  { value: 'vertical', label: 'Vertical' },
  { value: 'both', label: 'Both' },
];

/** Select control for the three supported flip directions. */
export function FlipDirectionSelect({
  value,
  onChange,
  label = 'Flip direction',
  error,
  className,
  id,
  ...props
}: FlipDirectionSelectProps) {
  const selectId = id ?? 'flip-direction';

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={selectId} className="mb-1.5 block text-sm font-medium text-foreground">
          {label}
        </label>
      )}
      <select
        id={selectId}
        value={value}
        onChange={(event) => onChange(event.target.value as FlipDirection)}
        aria-invalid={Boolean(error)}
        className={cn(
          'flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors duration-150',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'disabled:cursor-not-allowed disabled:opacity-50',
          error && 'border-destructive focus-visible:ring-destructive',
          className,
        )}
        {...props}
      >
        {FLIP_DIRECTION_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1.5 text-sm text-destructive">{error}</p>}
    </div>
  );
}
