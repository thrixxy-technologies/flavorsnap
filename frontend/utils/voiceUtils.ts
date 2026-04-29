// Voice utility functions for enhanced voice command processing

export interface VoiceCommandPattern {
  command: string;
  patterns: string[];
  confidence: number;
  language?: string;
}

export interface VoiceCalibrationData {
  userPatterns: Record<string, string[]>;
  confidence: Record<string, number>;
  language: string;
}

// Enhanced command patterns with confidence scoring
export const VOICE_PATTERNS: VoiceCommandPattern[] = [
  {
    command: 'upload',
    patterns: [
      'upload', 'open', 'camera', 'take picture', 'photo', 'image', 'select file',
      'télécharger', 'ouvrir', 'appareil photo', 'prendre photo', 'photo', 'image',
      'رفع', 'فتح', 'كاميرا', 'التقاط صورة', 'صورة', 'ملف',
      'fi', 'sii', 'kamẹra', 'ya aworan', 'aworan', 'faili'
    ],
    confidence: 0.9
  },
  {
    command: 'classify',
    patterns: [
      'classify', 'analyze', 'identify', 'recognize', 'what is this', 'food',
      'classifier', 'analyser', 'identifier', 'reconnaître', 'qu\'est-ce que c\'est',
      'تصنيف', 'تحليل', 'تحديد', 'تعرف', 'ما هذا', 'طعام',
      'ṣe ipin', 'ṣe ayẹwo', 'mọ', 'riri', 'kini yi', 'ounje'
    ],
    confidence: 0.9
  },
  {
    command: 'reset',
    patterns: [
      'reset', 'clear', 'start over', 'new', 'again', 'refresh',
      'réinitialiser', 'effacer', 'recommencer', 'nouveau', 'encore', 'rafraîchir',
      'إعادة تعيين', 'مسح', 'البدء من جديد', 'جديد', 'مرة أخرى', 'تحديث',
      'tunṣe', 'pa', 'bẹrẹ si', 'tuntun', 'mọ', 'fresh'
    ],
    confidence: 0.9
  },
  {
    command: 'help',
    patterns: [
      'help', 'assist', 'commands', 'what can i say', 'instructions',
      'aide', 'assistance', 'commandes', 'qu\'est-ce que je peux dire', 'instructions',
      'مساعدة', 'مساعدة', 'أوامر', 'ماذا يمكنني أن أقول', 'تعليمات',
      'iranlowo', 'iranlọwọ', 'awọn ibere', 'kini le mo so', 'ilana'
    ],
    confidence: 0.9
  },
  {
    command: 'cancel',
    patterns: [
      'cancel', 'stop', 'abort', 'never mind', 'forget it',
      'annuler', 'arrêter', 'abandonner', 'oublie ça',
      'إلغاء', 'توقف', 'إجهاض', 'انسى الأمر', 'لا يهم',
      'fagile', 'duro', 'fagile', 'gbagbe', 'ko si nkan'
    ],
    confidence: 0.9
  }
];

// Advanced pattern matching with fuzzy string matching
export const matchCommand = (transcript: string, calibration?: VoiceCalibrationData): string | null => {
  const normalizedTranscript = transcript.toLowerCase().trim();
  
  // Check user-specific patterns first if available
  if (calibration && calibration.userPatterns) {
    for (const [command, patterns] of Object.entries(calibration.userPatterns)) {
      for (const pattern of patterns) {
        if (normalizedTranscript.includes(pattern.toLowerCase())) {
          return command;
        }
      }
    }
  }
  
  // Check default patterns
  let bestMatch = null;
  let bestScore = 0;
  
  for (const patternData of VOICE_PATTERNS) {
    for (const pattern of patternData.patterns) {
      const score = calculateSimilarity(normalizedTranscript, pattern.toLowerCase());
      if (score > bestScore && score > 0.6) { // Minimum similarity threshold
        bestScore = score;
        bestMatch = patternData.command;
      }
    }
  }
  
  return bestMatch;
};

// Calculate string similarity using Levenshtein distance
export const calculateSimilarity = (str1: string, str2: string): number => {
  const longer = str1.length > str2.length ? str1 : str2;
  const shorter = str1.length > str2.length ? str2 : str1;
  
  if (longer.length === 0) return 1.0;
  
  const distance = levenshteinDistance(longer, shorter);
  return (longer.length - distance) / longer.length;
};

// Levenshtein distance implementation
export const levenshteinDistance = (str1: string, str2: string): number => {
  const matrix = [];
  
  for (let i = 0; i <= str2.length; i++) {
    matrix[i] = [i];
  }
  
  for (let j = 0; j <= str1.length; j++) {
    matrix[0][j] = j;
  }
  
  for (let i = 1; i <= str2.length; i++) {
    for (let j = 1; j <= str1.length; j++) {
      if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1,
          matrix[i][j - 1] + 1,
          matrix[i - 1][j] + 1
        );
      }
    }
  }
  
  return matrix[str2.length][str1.length];
};

// Voice calibration utilities
export const createCalibrationSession = (): VoiceCalibrationData => ({
  userPatterns: {},
  confidence: {},
  language: 'en'
});

export const addCalibrationPattern = (
  calibration: VoiceCalibrationData,
  command: string,
  pattern: string,
  confidence: number = 1.0
): VoiceCalibrationData => {
  const updated = { ...calibration };
  
  if (!updated.userPatterns[command]) {
    updated.userPatterns[command] = [];
  }
  
  updated.userPatterns[command].push(pattern);
  updated.confidence[command] = confidence;
  
  return updated;
};

// Error handling and retry logic
export class VoiceCommandError extends Error {
  constructor(
    message: string,
    public code: string,
    public retryable: boolean = false
  ) {
    super(message);
    this.name = 'VoiceCommandError';
  }
}

export const handleVoiceError = (error: any): VoiceCommandError => {
  const errorMessage = error?.message || error?.error || 'Unknown error';
  
  if (errorMessage.includes('not-allowed')) {
    return new VoiceCommandError(
      'Microphone permission denied. Please allow microphone access.',
      'PERMISSION_DENIED',
      false
    );
  }
  
  if (errorMessage.includes('no-speech')) {
    return new VoiceCommandError(
      'No speech detected. Please try again.',
      'NO_SPEECH',
      true
    );
  }
  
  if (errorMessage.includes('network')) {
    return new VoiceCommandError(
      'Network error. Please check your connection.',
      'NETWORK_ERROR',
      true
    );
  }
  
  if (errorMessage.includes('service-not-allowed')) {
    return new VoiceCommandError(
      'Speech recognition service not allowed. Please try again later.',
      'SERVICE_NOT_ALLOWED',
      true
    );
  }
  
  return new VoiceCommandError(
    `Voice recognition error: ${errorMessage}`,
    'UNKNOWN_ERROR',
    true
  );
};

// Retry logic with exponential backoff
export const retryWithBackoff = async <T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> => {
  let lastError: Error;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error as Error;
      
      if (attempt === maxRetries) {
        throw lastError;
      }
      
      const voiceError = handleVoiceError(error);
      if (!voiceError.retryable) {
        throw voiceError;
      }
      
      const delay = baseDelay * Math.pow(2, attempt);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError!;
};

// Audio level monitoring
export const monitorAudioLevel = (
  stream: MediaStream,
  callback: (level: number) => void
): () => void => {
  const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
  const analyser = audioContext.createAnalyser();
  const microphone = audioContext.createMediaStreamSource(stream);
  
  analyser.smoothingTimeConstant = 0.8;
  analyser.fftSize = 256;
  
  microphone.connect(analyser);
  
  const dataArray = new Uint8Array(analyser.frequencyBinCount);
  
  const checkAudioLevel = () => {
    analyser.getByteFrequencyData(dataArray);
    const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
    const normalizedLevel = Math.min(100, (average / 128) * 100);
    callback(normalizedLevel);
  };
  
  const intervalId = setInterval(checkAudioLevel, 100);
  
  return () => {
    clearInterval(intervalId);
    microphone.disconnect();
    audioContext.close();
  };
};

// Privacy-focused utilities
export const ensurePrivacyMode = (): boolean => {
  // Check if we're in a secure context
  if (typeof window !== 'undefined' && 
      (window.isSecureContext || 
       location.protocol === 'https:' || 
       location.hostname === 'localhost')) {
    return true;
  }
  return false;
};

export const clearVoiceData = (): void => {
  if (typeof window !== 'undefined') {
    // Clear any stored voice data
    localStorage.removeItem('voice_calibration');
    localStorage.removeItem('voice_patterns');
  }
};
