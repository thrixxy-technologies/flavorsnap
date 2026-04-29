"use client";
import { useState, useEffect, useCallback, useRef } from 'react';

export type VoiceCommand = 'upload' | 'classify' | 'reset' | 'help' | 'cancel';
export type Language = 'en' | 'fr' | 'ar' | 'yo';

interface VoiceCommandConfig {
  language: Language;
  continuous: boolean;
  interimResults: boolean;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  error?: any;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

// Command mappings for different languages
const COMMAND_MAPPINGS: Record<Language, Record<string, VoiceCommand>> = {
  en: {
    'upload': 'upload',
    'open': 'upload',
    'camera': 'upload',
    'take picture': 'upload',
    'classify': 'classify',
    'analyze': 'classify',
    'identify': 'classify',
    'reset': 'reset',
    'clear': 'reset',
    'start over': 'reset',
    'help': 'help',
    'cancel': 'cancel',
    'stop': 'cancel',
  },
  fr: {
    'télécharger': 'upload',
    'ouvrir': 'upload',
    'appareil photo': 'upload',
    'prendre photo': 'upload',
    'classifier': 'classify',
    'analyser': 'classify',
    'identifier': 'classify',
    'réinitialiser': 'reset',
    'effacer': 'reset',
    'recommencer': 'reset',
    'aide': 'help',
    'annuler': 'cancel',
    'arrêter': 'cancel',
  },
  ar: {
    'رفع': 'upload',
    'فتح': 'upload',
    'كاميرا': 'upload',
    'التقاط صورة': 'upload',
    'تصنيف': 'classify',
    'تحليل': 'classify',
    'تحديد': 'classify',
    'إعادة تعيين': 'reset',
    'مسح': 'reset',
    'البدء من جديد': 'reset',
    'مساعدة': 'help',
    'إلغاء': 'cancel',
    'توقف': 'cancel',
  },
  yo: {
    'fi': 'upload',
    'sii': 'upload',
    'kamẹra': 'upload',
    'ya aworan': 'upload',
    'ṣe ipin': 'classify',
    'ṣe ayẹwo': 'classify',
    'mọ': 'classify',
    'tunṣe': 'reset',
    'pa': 'reset',
    'bẹrẹ si': 'reset',
    'iranlowo': 'help',
    'fagile': 'cancel',
    'duro': 'cancel',
  },
};

const PHRASES: Record<Language, Record<string, string>> = {
  en: {
    listening: 'Listening...',
    processing: 'Processing...',
    ready: 'Voice control ready',
    error: 'Voice recognition error',
    notSupported: 'Voice recognition not supported',
    noMatch: 'No command recognized',
    tryAgain: 'Try again',
    commands: 'Available commands: upload, classify, reset, help, cancel',
  },
  fr: {
    listening: 'Écoute...',
    processing: 'Traitement...',
    ready: 'Contrôle vocal prêt',
    error: 'Erreur de reconnaissance vocale',
    notSupported: 'Reconnaissance vocale non supportée',
    noMatch: 'Aucune commande reconnue',
    tryAgain: 'Réessayez',
    commands: 'Commandes disponibles: télécharger, classifier, réinitialiser, aide, annuler',
  },
  ar: {
    listening: 'جاري الاستماع...',
    processing: 'جاري المعالجة...',
    ready: 'التحكم الصوتي جاهز',
    error: 'خطأ في التعرف الصوتي',
    notSupported: 'التعرف الصوتي غير مدعوم',
    noMatch: 'لم يتم التعرف على أي أمر',
    tryAgain: 'حاول مرة أخرى',
    commands: 'الأوامر المتاحة: رفع، تصنيف، إعادة تعيين، مساعدة، إلغاء',
  },
  yo: {
    listening: 'Gbọ́...',
    processing: 'N ṣe...',
    ready: 'Iṣakoso ohun ti o ṣee',
    error: 'Aṣiṣe ninu idanimọ ohun',
    notSupported: 'Idanimọ ohun kii ṣe atilẹyin',
    noMatch: 'Ko si ibere ti a mọ',
    tryAgain: 'Gbẹ́kẹ̀lé',
    commands: 'Awọn ibere ti o wa: fi, ṣe ipin, tunṣe, iranlowo, fagile',
  },
};

export const useVoiceCommands = (config: Partial<VoiceCommandConfig> = {}) => {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>(config.language || 'en');
  
  const recognitionRef = useRef<any>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const finalConfig: VoiceCommandConfig = {
    language: config.language || 'en',
    continuous: config.continuous || false,
    interimResults: config.interimResults || true,
    ...config,
  };

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        setIsSupported(true);
        
        // Configure recognition
        recognitionRef.current.continuous = finalConfig.continuous;
        recognitionRef.current.interimResults = finalConfig.interimResults;
        recognitionRef.current.lang = getLanguageCode(language);
        
        // Event handlers
        recognitionRef.current.onstart = () => {
          setIsListening(true);
          setError(null);
          setStatus(PHRASES[language].listening);
        };
        
        recognitionRef.current.onend = () => {
          setIsListening(false);
          setStatus(PHRASES[language].ready);
        };
        
        recognitionRef.current.onresult = (event: SpeechRecognitionEvent) => {
          let finalTranscript = '';
          let interimTranscript = '';
          
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            const transcript = result[0].transcript.toLowerCase();
            
            if (result.isFinal) {
              finalTranscript += transcript;
            } else {
              interimTranscript += transcript;
            }
          }
          
          setTranscript(finalTranscript || interimTranscript);
          
          if (finalTranscript) {
            processCommand(finalTranscript);
          }
        };
        
        recognitionRef.current.onerror = (event: any) => {
          setError(`${PHRASES[language].error}: ${event.error}`);
          setIsListening(false);
        };
        
        recognitionRef.current.onnomatch = () => {
          setStatus(PHRASES[language].noMatch);
          setTimeout(() => setStatus(PHRASES[language].ready), 2000);
        };
      } else {
        setIsSupported(false);
        setError(PHRASES[language].notSupported);
      }
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Update recognition language when language changes
  useEffect(() => {
    if (recognitionRef.current) {
      recognitionRef.current.lang = getLanguageCode(language);
    }
  }, [language]);

  const getLanguageCode = (lang: Language): string => {
    const codes: Record<Language, string> = {
      en: 'en-US',
      fr: 'fr-FR',
      ar: 'ar-SA',
      yo: 'yo-NG',
    };
    return codes[lang];
  };

  const processCommand = (transcript: string): VoiceCommand | null => {
    const commands = COMMAND_MAPPINGS[language];
    
    for (const [phrase, command] of Object.entries(commands)) {
      if (transcript.includes(phrase)) {
        setStatus(PHRASES[language].processing);
        return command;
      }
    }
    
    setStatus(PHRASES[language].noMatch);
    setTimeout(() => setStatus(PHRASES[language].ready), 2000);
    return null;
  };

  const startListening = useCallback(() => {
    if (!isSupported || !recognitionRef.current) {
      setError(PHRASES[language].notSupported);
      return;
    }
    
    try {
      recognitionRef.current.start();
      setTranscript('');
    } catch (err) {
      console.error('Failed to start speech recognition:', err);
      setError(PHRASES[language].error);
    }
  }, [isSupported, language]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
    }
  }, [isListening]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  const changeLanguage = useCallback((newLanguage: Language) => {
    setLanguage(newLanguage);
  }, []);

  return {
    isListening,
    isSupported,
    transcript,
    status,
    error,
    language,
    startListening,
    stopListening,
    toggleListening,
    changeLanguage,
    processCommand,
    phrases: PHRASES[language],
  };
};
