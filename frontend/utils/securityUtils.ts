
import DOMPurify from 'dompurify';

/**
 * Sanitizes HTML content to prevent XSS attacks.
 */
export const sanitizeHtml = (html: string): string => {
  if (typeof window === 'undefined') return html;
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
    ALLOWED_ATTR: ['href', 'target', 'rel'],
  });
};

/**
 * Escapes HTML characters to prevent XSS.
 */
export const escapeHtml = (text: string): string => {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
};

/**
 * Validates if a URL is safe (preventing javascript: pseudo-protocol).
 */
export const isSafeUrl = (url: string): boolean => {
  try {
    const parsed = new URL(url, window.location.origin);
    return ['http:', 'https:', 'mailto:', 'tel:'].includes(parsed.protocol);
  } catch {
    return false;
  }
};

/**
 * Securely handles sensitive data in logs by masking it.
 */
export const maskSensitiveData = (data: string): string => {
  if (!data) return '';
  if (data.length <= 4) return '****';
  return data.substring(0, 2) + '****' + data.substring(data.length - 2);
};

/**
 * Audit log helper.
 */
export const logSecurityEvent = (event: string, metadata: Record<string, any> = {}) => {
  console.info(`[SECURITY AUDIT] ${new Date().toISOString()} - ${event}`, metadata);
  // In a real app, this would send to a central logging server
};
