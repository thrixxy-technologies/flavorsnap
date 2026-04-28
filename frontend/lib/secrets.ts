import crypto from 'crypto';

export class SecretsManager {
  private static instance: SecretsManager;
  private encryptionKey: string;
  
  private constructor() {
    this.encryptionKey = process.env.ENCRYPTION_KEY || this.generateDefaultKey();
  }
  
  public static getInstance(): SecretsManager {
    if (!SecretsManager.instance) {
      SecretsManager.instance = new SecretsManager();
    }
    return SecretsManager.instance;
  }
  
  private generateDefaultKey(): string {
    // Generate a random key if none is provided (for development only)
    if (process.env.NODE_ENV === 'development') {
      console.warn('No ENCRYPTION_KEY provided. Using generated key for development only.');
      return crypto.randomBytes(32).toString('hex');
    }
    throw new Error('ENCRYPTION_KEY must be set in production');
  }
  
  public encrypt(text: string): string {
    try {
      const iv = crypto.randomBytes(16);
      const cipher = crypto.createCipher('aes-256-cbc', this.encryptionKey);
      let encrypted = cipher.update(text, 'utf8', 'hex');
      encrypted += cipher.final('hex');
      return iv.toString('hex') + ':' + encrypted;
    } catch (error) {
      console.error('Encryption error:', error);
      throw new Error('Failed to encrypt data');
    }
  }
  
  public decrypt(encryptedText: string): string {
    try {
      const parts = encryptedText.split(':');
      const iv = Buffer.from(parts[0], 'hex');
      const encrypted = parts[1];
      const decipher = crypto.createDecipher('aes-256-cbc', this.encryptionKey);
      let decrypted = decipher.update(encrypted, 'hex', 'utf8');
      decrypted += decipher.final('utf8');
      return decrypted;
    } catch (error) {
      console.error('Decryption error:', error);
      throw new Error('Failed to decrypt data');
    }
  }
  
  public hash(text: string): string {
    return crypto.createHash('sha256').update(text).digest('hex');
  }
  
  public generateSecureToken(length: number = 32): string {
    return crypto.randomBytes(length).toString('hex');
  }
  
  public validateJWTSecret(): boolean {
    const secret = process.env.JWT_SECRET;
    if (!secret) {
      throw new Error('JWT_SECRET must be set');
    }
    return secret.length >= 32;
  }
  
  public getSecureEnvVar(key: string): string | undefined {
    const value = process.env[key];
    if (!value) return undefined;
    
    // Check if the value is encrypted (starts with 'enc:')
    if (value.startsWith('enc:')) {
      try {
        return this.decrypt(value.substring(4));
      } catch (error) {
        console.error(`Failed to decrypt environment variable ${key}:`, error);
        return undefined;
      }
    }
    
    return value;
  }
  
  public setSecureEnvVar(key: string, value: string): void {
    const encrypted = this.encrypt(value);
    process.env[key] = `enc:${encrypted}`;
  }
  
  // Utility to validate required secrets
  public validateRequiredSecrets(secrets: string[]): { valid: boolean; missing: string[] } {
    const missing: string[] = [];
    
    for (const secret of secrets) {
      const value = this.getSecureEnvVar(secret);
      if (!value || value.trim() === '') {
        missing.push(secret);
      }
    }
    
    return {
      valid: missing.length === 0,
      missing
    };
  }
  
  // Environment-specific secret validation
  public validateEnvironmentSecrets(): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    const environment = process.env.NODE_ENV || 'development';
    
    // Common required secrets
    const commonSecrets = ['JWT_SECRET'];
    const commonValidation = this.validateRequiredSecrets(commonSecrets);
    
    if (!commonValidation.valid) {
      errors.push(`Missing common secrets: ${commonValidation.missing.join(', ')}`);
    }
    
    // Environment-specific secrets
    if (environment === 'production') {
      const prodSecrets = ['ENCRYPTION_KEY', 'DATABASE_URL'];
      const prodValidation = this.validateRequiredSecrets(prodSecrets);
      
      if (!prodValidation.valid) {
        errors.push(`Missing production secrets: ${prodValidation.missing.join(', ')}`);
      }
      
      // Additional production validations
      try {
        this.validateJWTSecret();
      } catch (error) {
        errors.push('JWT_SECRET is not valid for production');
      }
    }
    
    if (environment === 'staging') {
      const stagingSecrets = ['DATABASE_URL'];
      const stagingValidation = this.validateRequiredSecrets(stagingSecrets);
      
      if (!stagingValidation.valid) {
        errors.push(`Missing staging secrets: ${stagingValidation.missing.join(', ')}`);
      }
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  }
}

// Export singleton instance
export const secretsManager = SecretsManager.getInstance();

// Export convenience functions
export const encrypt = (text: string) => secretsManager.encrypt(text);
export const decrypt = (encryptedText: string) => secretsManager.decrypt(encryptedText);
export const hash = (text: string) => secretsManager.hash(text);
export const generateSecureToken = (length?: number) => secretsManager.generateSecureToken(length);
export const getSecureEnvVar = (key: string) => secretsManager.getSecureEnvVar(key);
export const setSecureEnvVar = (key: string, value: string) => secretsManager.setSecureEnvVar(key, value);
