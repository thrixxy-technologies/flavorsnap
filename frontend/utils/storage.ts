/**
 * A utility for managing localStorage with quota management and error handling.
 */

export const storage = {
  /**
   * Set an item in localStorage with error handling and quota management.
   */
  set: (key: string, value: any): boolean => {
    try {
      const serializedValue = JSON.stringify(value);
      
      // Basic check for size (optional, but good for reporting)
      // localStorage typically has a 5MB limit
      if (serializedValue.length > 4 * 1024 * 1024) {
        console.warn('Storage: Value is approaching 5MB limit');
      }

      localStorage.setItem(key, serializedValue);
      return true;
    } catch (error) {
      if (error instanceof DOMException && 
          (error.name === 'QuotaExceededError' || error.name === 'NS_ERROR_DOM_QUOTA_REACHED')) {
        console.error('Storage: Quota exceeded. Attempting to clear old data.');
        // If quota exceeded, we might want to clear some old data or inform the user
        // For now, let's just return false
      } else {
        console.error('Storage: Failed to save to localStorage', error);
      }
      return false;
    }
  },

  /**
   * Get an item from localStorage.
   */
  get: <T>(key: string, defaultValue: T): T => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.error('Storage: Failed to read from localStorage', error);
      return defaultValue;
    }
  },

  /**
   * Remove an item from localStorage.
   */
  remove: (key: string): void => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Storage: Failed to remove from localStorage', error);
    }
  },

  /**
   * Clear items that match a certain pattern or all items.
   */
  clear: (pattern?: string): void => {
    try {
      if (!pattern) {
        localStorage.clear();
        return;
      }

      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.includes(pattern)) {
          localStorage.removeItem(key);
        }
      });
    } catch (error) {
      console.error('Storage: Failed to clear localStorage', error);
    }
  }
};
