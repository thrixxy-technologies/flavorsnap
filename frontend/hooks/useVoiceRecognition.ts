'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

interface VoiceCommand {
  command: string;
  action: () => void;
  aliases?: string[];
}

interface VoiceRecognitionResult {
  transcript: string;
  confidence: number;
  isFinal: boolean;
  language: string;
}

type SupportedLanguage = 'en-US' | 'es-ES' | 'fr-FR' | 'de-DE' | 'it-IT' | 'ja-JP' | 'zh-CN';

export const useVoiceRecognition = () => {
  const recognitionRef = useRef<any>(null);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [confidence, setConfidence] = useState(0);
  const [language, setLanguage] = useState<SupportedLanguage>('en-US');
  const [commands, setCommands] = useState<VoiceCommand[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Initialize Web Speech API
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError('Speech Recognition API not supported in this browser');
      return;
    }

    const recognition = new SpeechRecognition();
    
    // Configure recognition
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.language = language;

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      let bestConfidence = 0;

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcriptSegment = event.results[i][0].transcript;
        const confidence = event.results[i][0].confidence;

        if (event.results[i].isFinal) {
          setTranscript((prev) => prev + transcriptSegment + ' ');
          bestConfidence = Math.max(bestConfidence, confidence);
          processCommand(transcriptSegment);
        } else {
          interimTranscript += transcriptSegment;
        }
      }

      if (interimTranscript) {
        setTranscript(interimTranscript);
        setConfidence(bestConfidence);
      }
    };

    recognition.onerror = (event: any) => {
      setError(`Error: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, [language]);

  const registerCommand = useCallback((command: VoiceCommand) => {
    setCommands((prev) => [...prev, command]);
  }, []);

  const unregisterCommand = useCallback((commandName: string) => {
    setCommands((prev) => prev.filter((cmd) => cmd.command !== commandName));
  }, []);

  const processCommand = useCallback(
    (transcript: string) => {
      const lowerTranscript = transcript.toLowerCase().trim();

      for (const cmd of commands) {
        if (
          lowerTranscript.includes(cmd.command.toLowerCase()) ||
          (cmd.aliases && cmd.aliases.some((alias) => lowerTranscript.includes(alias.toLowerCase())))
        ) {
          cmd.action();
          return;
        }
      }
    },
    [commands]
  );

  const startListening = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      setTranscript('');
      recognitionRef.current.start();
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
    }
  }, [isListening]);

  const abortListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.abort();
      setIsListening(false);
    }
  }, []);

  const changeLanguage = useCallback((newLanguage: SupportedLanguage) => {
    setLanguage(newLanguage);
    if (recognitionRef.current) {
      recognitionRef.current.language = newLanguage;
    }
  }, []);

  const getSupportedLanguages = useCallback(() => {
    return [
      { code: 'en-US', name: 'English (US)' },
      { code: 'es-ES', name: 'Spanish (Spain)' },
      { code: 'fr-FR', name: 'French' },
      { code: 'de-DE', name: 'German' },
      { code: 'it-IT', name: 'Italian' },
      { code: 'ja-JP', name: 'Japanese' },
      { code: 'zh-CN', name: 'Chinese (Simplified)' },
    ];
  }, []);

  // Built-in commands for food recognition
  useEffect(() => {
    const defaultCommands: VoiceCommand[] = [
      {
        command: 'recognize',
        action: () => console.log('Recognizing food...'),
        aliases: ['identify', 'scan', 'analyze'],
      },
      {
        command: 'nutrition',
        action: () => console.log('Showing nutrition...'),
        aliases: ['nutrients', 'calories', 'macros'],
      },
      {
        command: 'recipes',
        action: () => console.log('Showing recipes...'),
        aliases: ['recipe', 'cook', 'prepare'],
      },
      {
        command: 'history',
        action: () => console.log('Showing history...'),
        aliases: ['recent', 'previous'],
      },
    ];

    defaultCommands.forEach(registerCommand);
  }, [registerCommand]);

  const convertTextToSpeech = useCallback((text: string, language: SupportedLanguage = 'en-US') => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.language = language;
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;

    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
  }, []);

  const authenticateByVoice = useCallback(async (voiceData: string) => {
    try {
      const response = await fetch('/api/voice/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_data: voiceData }),
      });

      return await response.json();
    } catch (error) {
      console.error('Voice authentication error:', error);
      return null;
    }
  }, []);

  return {
    isListening,
    transcript,
    confidence,
    language,
    error,
    commands,
    startListening,
    stopListening,
    abortListening,
    registerCommand,
    unregisterCommand,
    changeLanguage,
    getSupportedLanguages,
    convertTextToSpeech,
    authenticateByVoice,
  };
};
