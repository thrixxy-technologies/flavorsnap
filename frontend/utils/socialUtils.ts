export const formatSocialStats = (count: number): string => {
  if (count >= 1000000) {
    return (count / 1000000).toFixed(1) + 'M';
  }
  if (count >= 1000) {
    return (count / 1000).toFixed(1) + 'K';
  }
  return count.toString();
};

export const generateSocialShareLink = (platform: 'twitter' | 'facebook' | 'linkedin', url: string, text: string) => {
  const encodedUrl = encodeURIComponent(url);
  const encodedText = encodeURIComponent(text);

  switch (platform) {
    case 'twitter':
      return `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedText}`;
    case 'facebook':
      return `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`;
    case 'linkedin':
      return `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`;
    default:
      return '';
  }
};

export const getSocialPreviewMetadata = (title: string, description: string, image: string) => {
  return {
    title,
    description,
    image,
    'og:title': title,
    'og:description': description,
    'og:image': image,
    'twitter:card': 'summary_large_image',
    'twitter:title': title,
    'twitter:description': description,
    'twitter:image': image,
  };
};
