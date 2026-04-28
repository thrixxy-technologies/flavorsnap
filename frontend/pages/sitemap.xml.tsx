import { GetServerSideProps } from 'next';

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://flavorsnap.com';

function generateSiteMap() {
  const now = new Date().toISOString();
  
  // Static pages with their SEO properties
  const staticPages = [
    {
      url: '/',
      lastModified: now,
      changeFrequency: 'daily',
      priority: 1.0,
    },
    {
      url: '/classify',
      lastModified: now,
      changeFrequency: 'daily',
      priority: 0.9,
    },
    {
      url: '/history',
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.7,
    },
    {
      url: '/about',
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.6,
    },
    {
      url: '/privacy',
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.5,
    },
    {
      url: '/terms',
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.5,
    },
    {
      url: '/contact',
      lastModified: now,
      changeFrequency: 'quarterly',
      priority: 0.4,
    },
    {
      url: '/blog',
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    {
      url: '/offline',
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.3,
    },
  ];

  // Generate dynamic food category pages
  const foodCategories = [
    'fruits', 'vegetables', 'grains', 'proteins', 'dairy', 
    'seafood', 'desserts', 'beverages', 'snacks', 'international'
  ];

  const categoryPages = foodCategories.map(category => ({
    url: `/category/${category}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.6,
  }));

  // Combine all pages
  const allPages = [...staticPages, ...categoryPages];

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
${allPages
  .map(
    (page) => `  <url>
    <loc>${siteUrl}${page.url}</loc>
    <lastmod>${page.lastModified}</lastmod>
    <changefreq>${page.changeFrequency}</changefreq>
    <priority>${page.priority}</priority>
    ${page.url === '/' ? `
    <xhtml:link rel="alternate" hreflang="en" href="${siteUrl}/" />
    <xhtml:link rel="alternate" hreflang="es" href="${siteUrl}/es/" />
    <xhtml:link rel="alternate" hreflang="fr" href="${siteUrl}/fr/" />
    <xhtml:link rel="alternate" hreflang="de" href="${siteUrl}/de/" />
    <xhtml:link rel="alternate" hreflang="ja" href="${siteUrl}/ja/" />
    <xhtml:link rel="alternate" hreflang="x-default" href="${siteUrl}/" />` : ''}
    ${page.url === '/' ? `
    <image:image>
      <image:loc>${siteUrl}/images/og-default.jpg</image:loc>
      <image:title>FlavorSnap - AI Food Classification</image:title>
      <image:caption>Instantly identify and analyze food with advanced machine learning</image:caption>
    </image:image>` : ''}
  </url>`
  )
  .join('\n')}
</urlset>`;
}

function SiteMap() {
  // getServerSideProps will do the heavy lifting
}

export const getServerSideProps: GetServerSideProps = async ({ res }) => {
  const sitemap = generateSiteMap();

  res.setHeader('Content-Type', 'text/xml');
  res.setHeader('Cache-Control', 'public, s-maxage=86400, stale-while-revalidate=43200');
  res.write(sitemap);
  res.end();

  return {
    props: {},
  };
};

export default SiteMap;