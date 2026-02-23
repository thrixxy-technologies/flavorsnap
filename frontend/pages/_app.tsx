import "@/styles/globals.css";
import type { AppProps } from "next/app";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { appWithTranslation } from "next-i18next";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AnalyticsProvider } from "@/lib/analytics-provider";
import { reportWebVitals } from "@/utils/performance";

function App({ Component, pageProps }: AppProps) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        refetchOnWindowFocus: false,
      },
    },
  }));

  return (
    <AnalyticsProvider>
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <Component {...pageProps} />
        </QueryClientProvider>
      </ErrorBoundary>
    </AnalyticsProvider>
  );
}

// Export reportWebVitals for Next.js to use
export { reportWebVitals };

export default appWithTranslation(App);
