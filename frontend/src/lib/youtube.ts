const YOUTUBE_URL_PATTERN =
  /^https?:\/\/(www\.)?(youtube\.com\/(watch\?v=|shorts\/|embed\/)[\w-]{6,}|youtu\.be\/[\w-]{6,})/i;

/** Basic client-side sanity check for a YouTube video URL before submitting. */
export function isValidYoutubeUrl(url: string): boolean {
  return YOUTUBE_URL_PATTERN.test(url.trim());
}
