import React from 'react';
import Head from 'next/head';
import SEOUtils, { SEOMetadata, StructuredData } from '@/utils/seoUtils';

interface SEOHeadProps {
  metadata: Partial<SEOMetadata>;
  structuredData?: StructuredData[];
  additionalStructuredData?: StructuredData[];
  noindex?: boolean;
  nofollow?: boolean;
  canonical?: string;
  hreflang?: string[];
  jsonLd?: StructuredData[];
}

const SEOHead: React.FC<SEOHeadProps> = ({
  metadata,
  structuredData = [],
  additionalStructuredData = [],
  noindex = false,
  nofollow = false,
  canonical,
  hreflang = ['en_US', 'es_ES', 'fr_FR', 'de_DE', 'ja_JP'],
  jsonLd = [],
}) => {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://flavorsnap.com';
  const fullUrl = canonical || (metadata.url ? `${siteUrl}${metadata.url}` : siteUrl);
  
  const {
    title,
    description,
    keywords,
    image,
    type = 'website',
    siteName = 'FlavorSnap',
    locale = 'en_US',
    author,
    publishedTime,
    modifiedTime,
    section,
    tags
  } = metadata;

  const fullTitle = title ? `${title} | ${siteName}` : siteName;
  const fullImage = image ? `${siteUrl}${image}` : `${siteUrl}/images/og-default.jpg`;

  // Combine all structured data
  const allStructuredData = [
    ...structuredData,
    ...additionalStructuredData,
    ...jsonLd,
  ];

  // Generate default structured data if none provided
  if (allStructuredData.length === 0 && metadata.url) {
    allStructuredData.push(SEOUtils.generateWebPageSchema(metadata));
  }

  const hreflangTags = hreflang.length > 0 ? SEOUtils.generateHreflangTags(metadata.url || '/', hreflang) : [];

  return (
    <Head>
      {/* Basic meta tags */}
      <title>{fullTitle}</title>
      <meta name="description" content={description || SEOUtils['DEFAULT_DESCRIPTION']} />
      <meta name="keywords" content={keywords?.join(', ') || 'food classification, AI, machine learning, food recognition, nutrition analysis, calorie counting'} />
      <meta name="author" content={author || 'FlavorSnap Team'} />
      <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
      
      {/* Robots meta */}
      <meta name="robots" content={`${noindex ? 'noindex' : 'index'}, ${nofollow ? 'nofollow' : 'follow'}`} />
      
      {/* Canonical URL */}
      <link rel="canonical" href={fullUrl} />
      
      {/* Open Graph tags */}
      <meta property="og:type" content={type} />
      <meta property="og:url" content={fullUrl} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description || SEOUtils['DEFAULT_DESCRIPTION']} />
      <meta property="og:image" content={fullImage} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />
      <meta property="og:image:alt" content={title || siteName} />
      <meta property="og:site_name" content={siteName} />
      <meta property="og:locale" content={locale} />
      
      {/* Twitter Card tags */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:site" content="@flavorsnap" />
      <meta name="twitter:creator" content="@flavorsnap" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description || SEOUtils['DEFAULT_DESCRIPTION']} />
      <meta name="twitter:image" content={fullImage} />
      
      {/* Article specific tags */}
      {type === 'article' && (
        <>
          {publishedTime && <meta property="article:published_time" content={publishedTime} />}
          {modifiedTime && <meta property="article:modified_time" content={modifiedTime} />}
          {author && <meta property="article:author" content={author} />}
          {section && <meta property="article:section" content={section} />}
          {tags?.map(tag => (
            <meta key={tag} property="article:tag" content={tag} />
          ))}
        </>
      )}
      
      {/* Hreflang tags */}
      {hreflangTags.map((tag, index) => (
        <link key={index} rel={tag.rel} hrefLang={tag.hrefLang} href={tag.href} />
      ))}
      
      {/* Icons and manifests */}
      <link rel="icon" href="/favicon.ico" sizes="any" />
      <link rel="icon" href="/icon.svg" type="image/svg+xml" />
      <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
      <link rel="manifest" href="/manifest.json" />
      
      {/* Preconnect and DNS prefetch */}
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link rel="dns-prefetch" href="//api.openai.com" />
      <link rel="dns-prefetch" href="//www.google-analytics.com" />
      
      {/* Additional meta tags for Core Web Vitals */}
      <meta name="format-detection" content="telephone=no" />
      <meta httpEquiv="x-ua-compatible" content="ie=edge" />
      <meta name="mobile-web-app-capable" content="yes" />
      <meta name="apple-mobile-web-app-capable" content="yes" />
      <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      <meta name="apple-mobile-web-app-title" content="FlavorSnap" />
      <meta name="theme-color" content="#10b981" />
      <meta name="msapplication-TileColor" content="#10b981" />
      <meta name="application-name" content={siteName} />
      
      {/* Security headers */}
      <meta name="referrer" content="strict-origin-when-cross-origin" />
      
      {/* Structured Data */}
      {allStructuredData.map((data, index) => (
        <script
          key={index}
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(data, null, 0),
          }}
        />
      ))}
      
      {/* Verification tags */}
      <meta name="google-site-verification" content="your-google-verification-code" />
      <meta name="msvalidate.01" content="your-bing-verification-code" />
      <meta name="yandex-verification" content="your-yandex-verification-code" />
      <meta name="p:domain_verify" content="your-pinterest-verification-code" />
      <meta name="facebook-domain-verification" content="your-facebook-verification-code" />
    </Head>
  );
};

export default SEOHead;
