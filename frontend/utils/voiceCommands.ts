/**
 * Voice Commands Configuration
 * Defines all available voice commands and their handlers
 */

export interface VoiceCommandConfig {
  command: string;
  aliases: string[];
  handler: () => void | Promise<void>;
  description: string;
  requiresAuthentication: boolean;
}

export const foodRecognitionCommands: VoiceCommandConfig[] = [
  {
    command: 'recognize food',
    aliases: ['identify food', 'scan food', 'analyze food', 'what is this'],
    handler: async () => {
      const event = new CustomEvent('voice-command:recognize-food');
      window.dispatchEvent(event);
    },
    description: 'Start food recognition from camera',
    requiresAuthentication: false,
  },
  {
    command: 'show nutrition',
    aliases: ['nutrition info', 'calories', 'macros', 'nutrients'],
    handler: async () => {
      const event = new CustomEvent('voice-command:show-nutrition');
      window.dispatchEvent(event);
    },
    description: 'Display nutritional information',
    requiresAuthentication: false,
  },
  {
    command: 'show recipes',
    aliases: ['recipes', 'cooking', 'how to cook', 'prepare'],
    handler: async () => {
      const event = new CustomEvent('voice-command:show-recipes');
      window.dispatchEvent(event);
    },
    description: 'Show recipes for recognized food',
    requiresAuthentication: false,
  },
];

export const navigationCommands: VoiceCommandConfig[] = [
  {
    command: 'go home',
    aliases: ['home', 'main page', 'dashboard'],
    handler: async () => {
      window.location.href = '/';
    },
    description: 'Navigate to home page',
    requiresAuthentication: false,
  },
  {
    command: 'show history',
    aliases: ['history', 'recent', 'my items'],
    handler: async () => {
      window.location.href = '/history';
    },
    description: 'Show recognition history',
    requiresAuthentication: true,
  },
  {
    command: 'open settings',
    aliases: ['settings', 'preferences', 'configuration'],
    handler: async () => {
      window.location.href = '/settings';
    },
    description: 'Open settings page',
    requiresAuthentication: true,
  },
];

export const controlCommands: VoiceCommandConfig[] = [
  {
    command: 'mute',
    aliases: ['silence', 'quiet', 'turn off sound'],
    handler: async () => {
      const event = new CustomEvent('voice-command:mute');
      window.dispatchEvent(event);
    },
    description: 'Mute audio feedback',
    requiresAuthentication: false,
  },
  {
    command: 'unmute',
    aliases: ['sound on', 'enable audio', 'turn on sound'],
    handler: async () => {
      const event = new CustomEvent('voice-command:unmute');
      window.dispatchEvent(event);
    },
    description: 'Unmute audio feedback',
    requiresAuthentication: false,
  },
  {
    command: 'help',
    aliases: ['commands', 'what can i say', 'guide'],
    handler: async () => {
      const event = new CustomEvent('voice-command:show-help');
      window.dispatchEvent(event);
    },
    description: 'Show available commands',
    requiresAuthentication: false,
  },
];

export const allCommands: VoiceCommandConfig[] = [
  ...foodRecognitionCommands,
  ...navigationCommands,
  ...controlCommands,
];

export function matchCommand(
  transcript: string,
  requiresAuthentication: boolean = false
): VoiceCommandConfig | null {
  const lowerTranscript = transcript.toLowerCase().trim();

  for (const cmd of allCommands) {
    if (requiresAuthentication && cmd.requiresAuthentication) {
      // Skip if authentication is required but not provided
      continue;
    }

    if (lowerTranscript === cmd.command.toLowerCase()) {
      return cmd;
    }

    for (const alias of cmd.aliases) {
      if (lowerTranscript === alias.toLowerCase()) {
        return cmd;
      }
    }

    // Partial matching for longer phrases
    if (cmd.command.toLowerCase().includes(lowerTranscript)) {
      return cmd;
    }
  }

  return null;
}

export function getCommandsByCategory(
  category: 'food' | 'navigation' | 'control'
): VoiceCommandConfig[] {
  switch (category) {
    case 'food':
      return foodRecognitionCommands;
    case 'navigation':
      return navigationCommands;
    case 'control':
      return controlCommands;
    default:
      return allCommands;
  }
}

export function generateCommandHelpText(): string {
  const categories = [
    { name: 'Food Recognition', commands: foodRecognitionCommands },
    { name: 'Navigation', commands: navigationCommands },
    { name: 'Control', commands: controlCommands },
  ];

  let helpText = '**Available Voice Commands:**\n\n';

  for (const category of categories) {
    helpText += `**${category.name}:**\n`;
    for (const cmd of category.commands) {
      helpText += `• ${cmd.command}`;
      if (cmd.aliases.length > 0) {
        helpText += ` (${cmd.aliases.join(', ')})`;
      }
      helpText += ` - ${cmd.description}\n`;
    }
    helpText += '\n';
  }

  return helpText;
}

export function validateVoiceInput(
  transcript: string,
  minLength: number = 3,
  maxLength: number = 100
): { valid: boolean; error?: string } {
  if (!transcript || transcript.trim().length < minLength) {
    return { valid: false, error: `Transcript too short (minimum ${minLength} characters)` };
  }

  if (transcript.length > maxLength) {
    return { valid: false, error: `Transcript too long (maximum ${maxLength} characters)` };
  }

  // Check for suspicious patterns
  if (/[<>\"'`]/.test(transcript)) {
    return { valid: false, error: 'Invalid characters detected' };
  }

  return { valid: true };
}
