import { NextSeoProps } from 'next-seo';

export interface SEOMetadata {
  title: string;
  description: string;
  keywords?: string[];
  image?: string;
  url?: string;
  type?: 'website' | 'article' | 'product';
  siteName?: string;
  locale?: string;
  author?: string;
  publishedTime?: string;
  modifiedTime?: string;
  section?: string;
  tags?: string[];
}

export interface StructuredData {
  '@context': string;
  '@type': string;
  name?: string;
  description?: string;
  image?: string | string[];
  url?: string;
  headline?: string;
  author?: {
    '@type': string;
    name: string;
  }[];
  publisher?: {
    '@type': string;
    name: string;
    logo?: {
      '@type': string;
      url: string;
    };
  };
  datePublished?: string;
  dateModified?: string;
  mainEntityOfPage?: {
    '@type': string;
    '@id': string;
  };
  [key: string]: any;
}

export interface WebVitals {
  lcp: number; // Largest Contentful Paint
  fid: number; // First Input Delay
  cls: number; // Cumulative Layout Shift
  fcp: number; // First Contentful Paint
  ttfb: number; // Time to First Byte
}

class SEOUtils {
  private static readonly DEFAULT_SITE_NAME = 'FlavorSnap';
  private static readonly DEFAULT_DESCRIPTION = 'AI-Powered Food Classification Web Application - Instantly identify and analyze food with advanced machine learning';
  private static readonly DEFAULT_LOCALE = 'en_US';
  private static readonly SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://flavorsnap.com';

  /**
   * Generate meta tags for a page
   */
  static generateMetaTags(metadata: Partial<SEOMetadata>): NextSeoProps {
    const {
      title,
      description,
      keywords,
      image,
      url,
      type = 'website',
      siteName = this.DEFAULT_SITE_NAME,
      locale = this.DEFAULT_LOCALE,
      author,
      publishedTime,
      modifiedTime,
      section,
      tags
    } = metadata;

    const fullTitle = title ? `${title} | ${siteName}` : siteName;
    const fullUrl = url ? `${this.SITE_URL}${url}` : this.SITE_URL;
    const fullImage = image ? `${this.SITE_URL}${image}` : `${this.SITE_URL}/images/og-default.jpg`;

    return {
      title: fullTitle,
      description: description || this.DEFAULT_DESCRIPTION,
      canonical: fullUrl,
      openGraph: {
        type,
        url: fullUrl,
        title: fullTitle,
        description: description || this.DEFAULT_DESCRIPTION,
        images: [
          {
            url: fullImage,
            width: 1200,
            height: 630,
            alt: title || siteName,
          },
        ],
        site_name: siteName,
        locale,
        article: type === 'article' ? {
          publishedTime,
          modifiedTime,
          authors: author ? [author] : undefined,
          section,
          tags,
        } : undefined,
      },
      twitter: {
        handle: '@flavorsnap',
        site: '@flavorsnap',
        cardType: 'summary_large_image',
      },
      additionalMetaTags: [
        {
          name: 'keywords',
          content: keywords?.join(', ') || 'food classification, AI, machine learning, food recognition, nutrition analysis, calorie counting',
        },
        {
          name: 'author',
          content: author || 'FlavorSnap Team',
        },
        {
          name: 'viewport',
          content: 'width=device-width, initial-scale=1, shrink-to-fit=no',
        },
        {
          name: 'theme-color',
          content: '#10b981',
        },
        {
          name: 'msapplication-TileColor',
          content: '#10b981',
        },
        {
          name: 'application-name',
          content: siteName,
        },
      ],
    };
  }

  /**
   * Generate structured data (JSON-LD)
   */
  static generateStructuredData(type: 'website' | 'article' | 'product' | 'recipe', data: any): StructuredData {
    const baseData = {
      '@context': 'https://schema.org',
      '@type': type === 'website' ? 'WebSite' : type === 'article' ? 'Article' : type === 'product' ? 'Product' : 'Recipe',
      url: data.url ? `${this.SITE_URL}${data.url}` : this.SITE_URL,
      name: data.title || this.DEFAULT_SITE_NAME,
      description: data.description || this.DEFAULT_DESCRIPTION,
      image: data.image ? `${this.SITE_URL}${data.image}` : `${this.SITE_URL}/images/og-default.jpg`,
    };

    switch (type) {
      case 'website':
        return {
          ...baseData,
          '@type': 'WebSite',
          potentialAction: {
            '@type': 'SearchAction',
            target: `${this.SITE_URL}/search?q={search_term_string}`,
            'query-input': 'required name=search_term_string',
          },
          publisher: {
            '@type': 'Organization',
            name: this.DEFAULT_SITE_NAME,
            url: this.SITE_URL,
            logo: {
              '@type': 'ImageObject',
              url: `${this.SITE_URL}/images/logo.png`,
            },
          },
        };

      case 'article':
        return {
          ...baseData,
          '@type': 'Article',
          headline: data.title,
          author: data.author ? [{
            '@type': 'Person',
            name: data.author,
          }] : [{
            '@type': 'Organization',
            name: 'FlavorSnap Team',
          }],
          publisher: {
            '@type': 'Organization',
            name: this.DEFAULT_SITE_NAME,
            logo: {
              '@type': 'ImageObject',
              url: `${this.SITE_URL}/images/logo.png`,
            },
          },
          datePublished: data.publishedTime || new Date().toISOString(),
          dateModified: data.modifiedTime || new Date().toISOString(),
          mainEntityOfPage: {
            '@type': 'WebPage',
            '@id': data.url ? `${this.SITE_URL}${data.url}` : this.SITE_URL,
          },
        };

      case 'product':
        return {
          ...baseData,
          '@type': 'Product',
          brand: {
            '@type': 'Brand',
            name: this.DEFAULT_SITE_NAME,
          },
          offers: {
            '@type': 'Offer',
            price: data.price || '0',
            priceCurrency: data.currency || 'USD',
            availability: 'https://schema.org/InStock',
          },
        };

      case 'recipe':
        return {
          ...baseData,
          '@type': 'Recipe',
          recipeCategory: data.category || 'Food',
          recipeCuisine: data.cuisine || 'International',
          nutrition: {
            '@type': 'NutritionInformation',
            calories: data.calories || '0 calories',
          },
          aggregateRating: data.rating ? {
            '@type': 'AggregateRating',
            ratingValue: data.rating,
            reviewCount: data.reviewCount || '1',
          } : undefined,
        };

      default:
        return baseData;
    }
  }

  /**
   * Generate breadcrumb structured data
   */
  static generateBreadcrumbSchema(breadcrumbs: Array<{ name: string; url: string }>): StructuredData {
    return {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: breadcrumbs.map((crumb, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        name: crumb.name,
        item: `${this.SITE_URL}${crumb.url}`,
      })),
    };
  }

  /**
   * Generate FAQ structured data
   */
  static generateFAQSchema(faqs: Array<{ question: string; answer: string }>): StructuredData {
    return {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: faqs.map(faq => ({
        '@type': 'Question',
        name: faq.question,
        acceptedAnswer: {
          '@type': 'Answer',
          text: faq.answer,
        },
      })),
    };
  }

  /**
   * Generate organization structured data
   */
  static generateOrganizationSchema(): StructuredData {
    return {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: this.DEFAULT_SITE_NAME,
      url: this.SITE_URL,
      logo: {
        '@type': 'ImageObject',
        url: `${this.SITE_URL}/images/logo.png`,
        width: 512,
        height: 512,
      },
      description: this.DEFAULT_DESCRIPTION,
      sameAs: [
        'https://twitter.com/flavorsnap',
        'https://facebook.com/flavorsnap',
        'https://instagram.com/flavorsnap',
        'https://linkedin.com/company/flavorsnap',
      ],
      contactPoint: {
        '@type': 'ContactPoint',
        contactType: 'customer service',
        email: 'support@flavorsnap.com',
      },
    };
  }

  /**
   * Generate WebPage structured data
   */
  static generateWebPageSchema(metadata: Partial<SEOMetadata>): StructuredData {
    return {
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: metadata.title || this.DEFAULT_SITE_NAME,
      description: metadata.description || this.DEFAULT_DESCRIPTION,
      url: metadata.url ? `${this.SITE_URL}${metadata.url}` : this.SITE_URL,
      inLanguage: metadata.locale || this.DEFAULT_LOCALE,
      isPartOf: {
        '@type': 'WebSite',
        name: this.DEFAULT_SITE_NAME,
        url: this.SITE_URL,
      },
      about: {
        '@type': 'Thing',
        name: 'Food Classification',
        description: 'AI-powered food recognition and analysis',
      },
    };
  }

  /**
   * Generate robots.txt content
   */
  static generateRobotsTxt(): string {
    return `# FlavorSnap Robots.txt
# Generated on ${new Date().toISOString()}

User-agent: *
Allow: /
Allow: /images/
Allow: /api/
Allow: /_next/static/

# Block AI crawlers from training data
User-agent: GPTBot
Disallow: /
User-agent: ChatGPT-User
Disallow: /
User-agent: CCBot
Disallow: /
User-agent: anthropic-ai
Disallow: /
User-agent: Claude-Web
Disallow: /

# Block common bot paths
Disallow: /admin/
Disallow: /api/admin/
Disallow: /_next/
Disallow: /static/
Disallow: /.well-known/

# Allow specific important paths
Allow: /sitemap.xml
Allow: /robots.txt

# Sitemap location
Sitemap: ${this.SITE_URL}/sitemap.xml

# Crawl delay (optional)
Crawl-delay: 1

# Host directive (for Yandex)
Host: ${this.SITE_URL}
`;
  }

  /**
   * Generate sitemap entries
   */
  static generateSitemapEntries(): Array<{
    url: string;
    lastModified: string;
    changeFrequency: string;
    priority: number;
  }> {
    const now = new Date().toISOString();
    
    return [
      {
        url: this.SITE_URL,
        lastModified: now,
        changeFrequency: 'daily',
        priority: 1.0,
      },
      {
        url: `${this.SITE_URL}/classify`,
        lastModified: now,
        changeFrequency: 'daily',
        priority: 0.9,
      },
      {
        url: `${this.SITE_URL}/history`,
        lastModified: now,
        changeFrequency: 'weekly',
        priority: 0.7,
      },
      {
        url: `${this.SITE_URL}/about`,
        lastModified: now,
        changeFrequency: 'monthly',
        priority: 0.6,
      },
      {
        url: `${this.SITE_URL}/privacy`,
        lastModified: now,
        changeFrequency: 'monthly',
        priority: 0.5,
      },
      {
        url: `${this.SITE_URL}/terms`,
        lastModified: now,
        changeFrequency: 'monthly',
        priority: 0.5,
      },
    ];
  }

  /**
   * Format Web Vitals for reporting
   */
  static formatWebVitals(vitals: WebVitals): string {
    return JSON.stringify({
      lcp: `${vitals.lcp}ms`,
      fid: `${vitals.fid}ms`,
      cls: vitals.cls.toFixed(3),
      fcp: `${vitals.fcp}ms`,
      ttfb: `${vitals.ttfb}ms`,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Generate social media share URLs
   */
  static generateShareUrls(url: string, title: string, description: string): {
    twitter: string;
    facebook: string;
    linkedin: string;
    whatsapp: string;
    email: string;
  } {
    const encodedUrl = encodeURIComponent(url);
    const encodedTitle = encodeURIComponent(title);
    const encodedDescription = encodeURIComponent(description);

    return {
      twitter: `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}&via=flavorsnap`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`,
      whatsapp: `https://wa.me/?text=${encodedTitle}%20${encodedUrl}`,
      email: `mailto:?subject=${encodedTitle}&body=${encodedDescription}%20${encodedUrl}`,
    };
  }

  /**
   * Generate structured data for food classification results
   */
  static generateFoodClassificationSchema(result: {
    food: string;
    confidence: number;
    calories?: number;
    imageUrl?: string;
  }): StructuredData {
    return {
      '@context': 'https://schema.org',
      '@type': 'Recipe',
      name: result.food,
      description: `AI-identified food item with ${(result.confidence * 100).toFixed(1)}% confidence`,
      image: result.imageUrl,
      nutrition: result.calories ? {
        '@type': 'NutritionInformation',
        calories: `${result.calories} calories`,
      } : undefined,
      aggregateRating: {
        '@type': 'AggregateRating',
        ratingValue: (result.confidence * 5).toFixed(1), // Convert to 5-star scale
        reviewCount: '1',
        bestRating: '5',
        worstRating: '1',
      },
    };
  }

  /**
   * Generate hreflang tags for internationalization
   */
  static generateHreflangTags(url: string, locales: string[]): Array<{
    rel: string;
    hrefLang: string;
    href: string;
  }> {
    const baseUrl = url.startsWith('/') ? `${this.SITE_URL}${url}` : url;
    
    return locales.map(locale => ({
      rel: 'alternate',
      hrefLang: locale,
      href: `${baseUrl}?lang=${locale}`,
    }));
  }
}

export default SEOUtils;
