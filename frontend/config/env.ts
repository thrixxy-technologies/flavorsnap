/**
 * Environment Variable Validation
 * Validates required environment variables at startup and provides
 * fallback values for optional ones.
 */

interface EnvSchema {
  key: string;
  required: boolean;
  fallback?: string;
  description: string;
}

const ENV_SCHEMA: EnvSchema[] = [
  { key: 'NEXT_PUBLIC_API_URL', required: true, description: 'Backend API URL' },
  { key: 'NEXT_PUBLIC_STELLAR_NETWORK', required: false, fallback: 'testnet', description: 'Stellar network' },
  { key: 'NEXT_PUBLIC_HORIZON_URL', required: false, fallback: 'https://horizon-testnet.stellar.org', description: 'Stellar Horizon URL' },
  { key: 'NEXT_PUBLIC_CONTRACT_ID', required: false, fallback: '', description: 'Deployed contract ID' },
  { key: 'NEXT_PUBLIC_GA_ID', required: false, fallback: '', description: 'Google Analytics ID' },
  { key: 'NEXT_PUBLIC_SENTRY_DSN', required: false, fallback: '', description: 'Sentry DSN for error tracking' },
  { key: 'DATABASE_URL', required: false, fallback: 'postgresql://localhost:5432/flavorsnap', description: 'Database connection URL' },
  { key: 'REDIS_URL', required: false, fallback: 'redis://localhost:6379', description: 'Redis connection URL' },
];

export interface ValidatedEnv {
  [key: string]: string;
}

/**
 * Validate environment variables against the schema.
 * Throws if required variables are missing.
 */
export function validateEnv(): ValidatedEnv {
  const result: ValidatedEnv = {};
  const missing: string[] = [];

  for (const schema of ENV_SCHEMA) {
    const value = process.env[schema.key];

    if (value) {
      result[schema.key] = value;
    } else if (schema.fallback !== undefined) {
      result[schema.key] = schema.fallback;
    } else if (schema.required) {
      missing.push(schema.key);
    }
  }

  if (missing.length > 0) {
    const message = `Missing required environment variables: ${missing.join(', ')}.\n` +
      `Please check your .env file. See .env.example for reference.`;
    if (process.env.NODE_ENV === 'production') {
      throw new Error(message);
    } else {
      console.warn(`[ENV WARNING] ${message}`);
    }
  }

  return result;
}

/**
 * Get a validated environment variable value.
 */
export function getEnv(key: string): string {
  const schema = ENV_SCHEMA.find(s => s.key === key);
  if (!schema) {
    return process.env[key] || '';
  }
  return process.env[key] || schema.fallback || '';
}

/**
 * Check if running in production.
 */
export function isProduction(): boolean {
  return process.env.NODE_ENV === 'production';
}

// Validate on import (non-blocking in development)
if (typeof window === 'undefined') {
  try {
    validateEnv();
  } catch (e) {
    console.error('[ENV] Validation failed:', e);
  }
}
