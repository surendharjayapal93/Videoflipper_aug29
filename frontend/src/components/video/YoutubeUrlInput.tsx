import { Input, type InputProps } from '@/components/ui/Input';

export type YoutubeUrlInputProps = Omit<InputProps, 'type'>;

/** Text input pre-configured for pasting a YouTube video URL. */
export function YoutubeUrlInput({
  label = 'YouTube URL',
  placeholder = 'https://www.youtube.com/watch?v=...',
  ...props
}: YoutubeUrlInputProps) {
  return <Input type="url" label={label} placeholder={placeholder} {...props} />;
}
