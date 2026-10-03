export const MAX_UPLOAD_MB = 20;
export const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md", ".markdown"];
export const ACCEPT_ATTR = ACCEPTED_EXTENSIONS.join(",");

/** Client-side checks for fast feedback. The server re-validates everything (magic bytes). */
export function validateFile(file: File, maxMb = MAX_UPLOAD_MB): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return "Unsupported type. Upload PDF, DOCX, TXT or Markdown.";
  }
  if (file.size === 0) return "The file is empty.";
  if (file.size > maxMb * 1024 * 1024) return `Larger than ${maxMb} MB.`;
  return null;
}
