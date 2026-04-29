import { config as dotenvConfig } from 'dotenv';
import path from 'path';
import fs from 'fs';

// Load environment variables
dotenvConfig();

interface AppConfig {
  app: {
    name: string;
    version: string;
    environment: string;
    debug: boolean;
    hotReload: boolean;
  };
  api: {
    baseUrl: string;
    timeout: number;
    retries: number;
  };
  stellar: {
    network: string;
    rpcUrl: string;
    contractId: string;
  };
  ml: {
    modelPath: string;
    classesPath: string;
    confidenceThreshold: number;
  };
  upload: {
    maxFileSize: number;
    uploadDir: string;
    allowedTypes: string[];
    tempDir: string;
  };
  security: {
    jwtExpiry: string;
    bcryptRounds: number;
    rateLimitWindow: number;
    rateLimitMax: number;
  };
  logging: {
    level: string;
    format: string;
    colorize: boolean;
    timestamp: boolean;
  };
  features: {
    mlClassification: boolean;
    blockchainIntegration: boolean;
    analytics: boolean;
    cacheEnabled: boolean;
  };
}

function loadConfigFile(): AppConfig {
  const environment = process.env.NODE_ENV || 'development';
  const configPath = path.join(process.cwd(), '..', 'config', 'environments', `${environment}.json`);
  
  try {
    if (fs.existsSync(configPath)) {
      const configData = fs.readFileSync(configPath, 'utf-8');
      const config = JSON.parse(configData);
      
      // Replace environment variables in config
      return replaceEnvVars(config);
    } else {
      console.warn(`Config file not found for environment: ${environment}. Using development config.`);
      return getDefaultConfig();
    }
  } catch (error) {
    console.error('Error loading config:', error);
    return getDefaultConfig();
  }
}

function replaceEnvVars(obj: any): any {
  if (typeof obj === 'string') {
    return obj.replace(/\$\{([^}]+)\}/g, (match, envVar) => {
      return process.env[envVar] || match;
    });
  } else if (Array.isArray(obj)) {
    return obj.map(item => replaceEnvVars(item));
  } else if (obj !== null && typeof obj === 'object') {
    const result: any = {};
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        result[key] = replaceEnvVars(obj[key]);
      }
    }
    return result;
  }
  return obj;
}

function getDefaultConfig(): AppConfig {
  return {
    app: {
      name: 'FlavorSnap',
      version: '0.1.0',
      environment: 'development',
      debug: true,
      hotReload: true
    },
    api: {
      baseUrl: 'http://localhost:3000/api',
      timeout: 30000,
      retries: 3
    },
    stellar: {
      network: 'testnet',
      rpcUrl: 'https://soroban-testnet.stellar.org',
      contractId: ''
    },
    ml: {
      modelPath: 'models/best_model.pth',
      classesPath: 'food_classes.txt',
      confidenceThreshold: 0.7
    },
    upload: {
      maxFileSize: 10485760,
      uploadDir: 'uploads',
      allowedTypes: ['jpg', 'jpeg', 'png', 'gif'],
      tempDir: 'temp'
    },
    security: {
      jwtExpiry: '24h',
      bcryptRounds: 10,
      rateLimitWindow: 900000,
      rateLimitMax: 100
    },
    logging: {
      level: 'debug',
      format: 'dev',
      colorize: true,
      timestamp: true
    },
    features: {
      mlClassification: true,
      blockchainIntegration: true,
      analytics: false,
      cacheEnabled: false
    }
  };
}

// Merge environment variables with config
function mergeWithEnvVars(config: AppConfig): AppConfig {
  return {
    ...config,
    app: {
      ...config.app,
      environment: process.env.NODE_ENV || config.app.environment
    },
    api: {
      ...config.api,
      baseUrl: process.env.NEXT_PUBLIC_API_URL || config.api.baseUrl
    },
    stellar: {
      ...config.stellar,
      network: process.env.STELLAR_NETWORK || config.stellar.network,
      rpcUrl: process.env.SOROBAN_RPC_URL || config.stellar.rpcUrl,
      contractId: process.env.CONTRACT_ID || config.stellar.contractId
    },
    ml: {
      ...config.ml,
      modelPath: process.env.MODEL_PATH || config.ml.modelPath,
      classesPath: process.env.MODEL_CLASSES_PATH || config.ml.classesPath
    },
    upload: {
      ...config.upload,
      maxFileSize: parseInt(process.env.MAX_FILE_SIZE || config.upload.maxFileSize.toString()),
      uploadDir: process.env.UPLOAD_DIR || config.upload.uploadDir,
      allowedTypes: (process.env.ALLOWED_FILE_TYPES || config.upload.allowedTypes.join(',')).split(',')
    },
    features: {
      ...config.features,
      mlClassification: process.env.ENABLE_ML_CLASSIFICATION === 'true',
      blockchainIntegration: process.env.ENABLE_BLOCKCHAIN_INTEGRATION === 'true',
      analytics: process.env.ENABLE_ANALYTICS === 'true'
    }
  };
}

export const config = mergeWithEnvVars(loadConfigFile());

// Export individual config sections for convenience
export const appConfig = config.app;
export const apiConfig = config.api;
export const stellarConfig = config.stellar;
export const mlConfig = config.ml;
export const uploadConfig = config.upload;
export const securityConfig = config.security;
export const loggingConfig = config.logging;
export const featuresConfig = config.features;

// Utility function to check if a feature is enabled
export function isFeatureEnabled(feature: keyof typeof featuresConfig): boolean {
  return config.features[feature];
}

// Utility function to get environment-specific values
export function getEnvVar(key: string, defaultValue?: string): string {
  return process.env[key] || defaultValue || '';
}
