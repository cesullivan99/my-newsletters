export const API_CONFIG = {
  BASE_URL: 'http://localhost:5001', // Update for production
  WEBSOCKET_URL: 'ws://localhost:5001', // Update for production
  TIMEOUT: 10000, // 10 seconds
} as const;

export const VOICE_CONFIG = {
  SAMPLE_RATE: 16000,
  CHANNELS: 1,
  AUDIO_ENCODING: 'PCM_16BIT',
  MAX_RECORDING_DURATION: 30000, // 30 seconds
  MIN_RECORDING_DURATION: 500, // 0.5 seconds
} as const;

export const UI_COLORS = {
  PRIMARY: '#2563eb',
  SECONDARY: '#64748b',
  SUCCESS: '#10b981',
  ERROR: '#ef4444',
  WARNING: '#f59e0b',
  
  BACKGROUND: '#ffffff',
  SURFACE: '#f8fafc',
  TEXT_PRIMARY: '#1e293b',
  TEXT_SECONDARY: '#64748b',
  TEXT_LIGHT: '#94a3b8',
  
  DARK_BACKGROUND: '#0f172a',
  DARK_SURFACE: '#1e293b',
  DARK_TEXT_PRIMARY: '#f8fafc',
  DARK_TEXT_SECONDARY: '#cbd5e1',
} as const;

export const BRIEFING_STATES = {
  IDLE: 'idle',
  LOADING: 'loading',
  PLAYING: 'playing',
  PAUSED: 'paused',
  LISTENING: 'listening',
  COMPLETED: 'completed',
  ERROR: 'error',
} as const;

export const VOICE_COMMANDS = {
  SKIP: ['skip', 'next', 'move on'],
  TELL_MORE: ['tell me more', 'go deeper', 'full story'],
  METADATA: ['what newsletter', 'when published', 'source'],
  PAUSE: ['pause', 'stop'],
  RESUME: ['resume', 'continue'],
} as const;

export const STORAGE_KEYS = {
  AUTH_TOKEN: '@auth_token',
  USER_PREFERENCES: '@user_preferences',
  CACHED_BRIEFINGS: '@cached_briefings',
} as const;

export const VOICE_TYPES = {
  DEFAULT: 'eleven_monolingual_v1',
  PREMIUM: 'eleven_multilingual_v2',
  FAST: 'eleven_turbo_v2',
} as const;

export const PERMISSIONS = {
  MICROPHONE: 'android.permission.RECORD_AUDIO',
  STORAGE: 'android.permission.WRITE_EXTERNAL_STORAGE',
} as const;