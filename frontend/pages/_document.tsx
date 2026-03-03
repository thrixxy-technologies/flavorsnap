import { Html, Head, Main, NextScript } from "next/document";
import type { DocumentProps } from "next/document";

const rtlLocales = ["ar"];

export default function Document(props: DocumentProps) {
  const locale = props.__NEXT_DATA__?.locale || "en";
  const dir = rtlLocales.includes(locale) ? "rtl" : "ltr";

  return (
    <Html lang={locale} dir={dir}>
      <Head>
        {/* PWA Meta Tags */}
        <meta name="theme-color" content="#ffa500" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="FlavorSnap" />
        <meta name="application-name" content="FlavorSnap" />
        <meta name="msapplication-TileColor" content="#ffa500" />
        <meta name="msapplication-config" content="/browserconfig.xml" />
        
        {/* PWA Icons */}
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" sizes="72x72" href="/icons/icon-72x72.png" />
        <link rel="apple-touch-icon" sizes="96x96" href="/icons/icon-96x96.png" />
        <link rel="apple-touch-icon" sizes="128x128" href="/icons/icon-128x128.png" />
        <link rel="apple-touch-icon" sizes="144x144" href="/icons/icon-144x144.png" />
        <link rel="apple-touch-icon" sizes="152x152" href="/icons/icon-152x152.png" />
        <link rel="apple-touch-icon" sizes="192x192" href="/icons/icon-192x192.png" />
        <link rel="apple-touch-icon" sizes="384x384" href="/icons/icon-384x384.png" />
        <link rel="apple-touch-icon" sizes="512x512" href="/icons/icon-512x512.png" />
        
        {/* Standard Icons */}
        <link rel="icon" type="image/png" sizes="32x32" href="/icons/icon-32x32.png" />
        <link rel="icon" type="image/png" sizes="16x16" href="/icons/icon-16x16.png" />
        <link rel="shortcut icon" href="/favicon.ico" />
        
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <meta name="format-detection" content="telephone=no" />
      </Head>
      <body className="antialiased">
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
