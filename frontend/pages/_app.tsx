import "@/styles/globals.css";
import "@/styles/accessibility.css";
import "@/styles/mobile-responsive.css";
import type { AppProps } from "next/app";
import ErrorBoundary from "@/components/ErrorBoundary";
import { ThemeProvider } from "@/components/ThemeProvider";
import NotificationSystem from "@/components/NotificationSystem";
import { appWithTranslation } from 'next-i18next';
import { StoreProvider } from '@/frontend/store/index';
import type { ValidationError } from '@/frontend/store/index';
import StateDebugger from '@/frontend/components/StateDebugger';

// reportWebVitals can be imported from a utils file if you have one
// import { reportWebVitals } from '@/utils/web-vitals';

const handleValidationError = (errors: ValidationError[]) => {
  if (process.env.NODE_ENV === 'development') {
    console.warn('[StoreProvider] Validation error:', errors);
  }
};

function App({ Component, pageProps }: AppProps) {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        <StoreProvider onValidationError={handleValidationError}>
          <Component {...pageProps} />
          <NotificationSystem />
          <StateDebugger />
        </StoreProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default appWithTranslation(App);