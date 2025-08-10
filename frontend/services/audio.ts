import AudioRecorderPlayer, {
  AVEncoderAudioQualityIOSType,
  AVEncodingOption,
  AudioEncoderAndroidType,
  AudioSet,
  AudioSourceAndroidType,
} from 'react-native-audio-recorder-player';
import {Platform} from 'react-native';
import {check, request, PERMISSIONS, RESULTS} from 'react-native-permissions';
import {VOICE_CONFIG} from '../utils/constants';

export interface AudioRecordingConfig {
  sampleRate?: number;
  channels?: number;
  bitsPerSample?: number;
  wavFile?: string;
}

export interface PlaybackState {
  currentPositionSec: number;
  currentDurationSec: number;
  playTime: string;
  duration: string;
}

export interface RecordingState {
  recordSecs: number;
  recordTime: string;
}

class AudioService {
  private audioRecorderPlayer: AudioRecorderPlayer;
  private recordingPath: string | null = null;
  private isRecording = false;
  private isPlaying = false;

  constructor() {
    this.audioRecorderPlayer = new AudioRecorderPlayer();
    this.audioRecorderPlayer.setSubscriptionDuration(0.1); // Update every 100ms
  }

  async requestPermissions(): Promise<boolean> {
    try {
      const permission = Platform.select({
        android: PERMISSIONS.ANDROID.RECORD_AUDIO,
        ios: PERMISSIONS.IOS.MICROPHONE,
      });

      if (!permission) return false;

      const result = await check(permission);
      
      if (result === RESULTS.GRANTED) {
        return true;
      }

      const requestResult = await request(permission);
      return requestResult === RESULTS.GRANTED;
    } catch (error) {
      console.error('Error requesting audio permissions:', error);
      return false;
    }
  }

  private getAudioConfig(): AudioSet {
    return {
      AudioEncoderAndroid: AudioEncoderAndroidType.AAC,
      AudioSourceAndroid: AudioSourceAndroidType.MIC,
      AVEncoderAudioQualityKeyIOS: AVEncoderAudioQualityIOSType.high,
      AVNumberOfChannelsKeyIOS: VOICE_CONFIG.CHANNELS,
      AVFormatIDKeyIOS: AVEncodingOption.aac,
      AVSampleRateKeyIOS: VOICE_CONFIG.SAMPLE_RATE,
    };
  }

  async startRecording(
    config?: AudioRecordingConfig,
    onProgress?: (state: RecordingState) => void
  ): Promise<string> {
    try {
      const hasPermission = await this.requestPermissions();
      if (!hasPermission) {
        throw new Error('Audio recording permission denied');
      }

      const audioConfig = this.getAudioConfig();
      
      // Set up progress listener
      if (onProgress) {
        this.audioRecorderPlayer.addRecordBackListener((e) => {
          onProgress({
            recordSecs: e.currentPosition,
            recordTime: this.audioRecorderPlayer.mmssss(
              Math.floor(e.currentPosition)
            ),
          });
        });
      }

      this.recordingPath = await this.audioRecorderPlayer.startRecorder(
        undefined, // Use default path
        audioConfig
      );

      this.isRecording = true;
      return this.recordingPath;
    } catch (error) {
      console.error('Error starting recording:', error);
      throw error;
    }
  }

  async stopRecording(): Promise<string> {
    try {
      if (!this.isRecording) {
        throw new Error('No recording in progress');
      }

      const result = await this.audioRecorderPlayer.stopRecorder();
      this.audioRecorderPlayer.removeRecordBackListener();
      this.isRecording = false;
      
      return result;
    } catch (error) {
      console.error('Error stopping recording:', error);
      throw error;
    }
  }

  async startPlayback(
    audioPath: string,
    onProgress?: (state: PlaybackState) => void
  ): Promise<void> {
    try {
      // Set up progress listener
      if (onProgress) {
        this.audioRecorderPlayer.addPlayBackListener((e) => {
          onProgress({
            currentPositionSec: e.currentPosition,
            currentDurationSec: e.duration,
            playTime: this.audioRecorderPlayer.mmssss(
              Math.floor(e.currentPosition)
            ),
            duration: this.audioRecorderPlayer.mmssss(Math.floor(e.duration)),
          });
        });
      }

      await this.audioRecorderPlayer.startPlayer(audioPath);
      this.isPlaying = true;
    } catch (error) {
      console.error('Error starting playback:', error);
      throw error;
    }
  }

  async pausePlayback(): Promise<void> {
    try {
      await this.audioRecorderPlayer.pausePlayer();
    } catch (error) {
      console.error('Error pausing playback:', error);
      throw error;
    }
  }

  async resumePlayback(): Promise<void> {
    try {
      await this.audioRecorderPlayer.resumePlayer();
    } catch (error) {
      console.error('Error resuming playback:', error);
      throw error;
    }
  }

  async stopPlayback(): Promise<void> {
    try {
      await this.audioRecorderPlayer.stopPlayer();
      this.audioRecorderPlayer.removePlayBackListener();
      this.isPlaying = false;
    } catch (error) {
      console.error('Error stopping playback:', error);
      throw error;
    }
  }

  async seekTo(position: number): Promise<void> {
    try {
      await this.audioRecorderPlayer.seekToPlayer(position);
    } catch (error) {
      console.error('Error seeking audio:', error);
      throw error;
    }
  }

  async setPlaybackSpeed(speed: number): Promise<void> {
    try {
      // Speed should be between 0.5 and 2.0
      const clampedSpeed = Math.max(0.5, Math.min(2.0, speed));
      await this.audioRecorderPlayer.setSpeed(clampedSpeed);
    } catch (error) {
      console.error('Error setting playback speed:', error);
      throw error;
    }
  }

  async setVolume(volume: number): Promise<void> {
    try {
      // Volume should be between 0.0 and 1.0
      const clampedVolume = Math.max(0.0, Math.min(1.0, volume));
      await this.audioRecorderPlayer.setVolume(clampedVolume);
    } catch (error) {
      console.error('Error setting volume:', error);
      throw error;
    }
  }

  // Convert audio file to base64 for transmission
  async audioFileToBase64(filePath: string): Promise<string> {
    try {
      const RNFS = require('react-native-fs');
      const base64 = await RNFS.readFile(filePath, 'base64');
      return base64;
    } catch (error) {
      console.error('Error converting audio to base64:', error);
      throw error;
    }
  }

  // Convert base64 to audio buffer for WebSocket transmission
  base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binaryString = atob(base64);
    const buffer = new ArrayBuffer(binaryString.length);
    const uint8Array = new Uint8Array(buffer);
    
    for (let i = 0; i < binaryString.length; i++) {
      uint8Array[i] = binaryString.charCodeAt(i);
    }
    
    return buffer;
  }

  // Audio visualization helper - get audio levels
  async getAudioLevel(): Promise<number> {
    try {
      // This would require native module implementation
      // For now, return a mock value
      return Math.random() * 100;
    } catch (error) {
      console.error('Error getting audio level:', error);
      return 0;
    }
  }

  // Clean up resources
  async cleanup(): Promise<void> {
    try {
      if (this.isRecording) {
        await this.stopRecording();
      }
      if (this.isPlaying) {
        await this.stopPlayback();
      }
      
      this.audioRecorderPlayer.removeRecordBackListener();
      this.audioRecorderPlayer.removePlayBackListener();
    } catch (error) {
      console.error('Error cleaning up audio service:', error);
    }
  }

  // Getters
  get recording(): boolean {
    return this.isRecording;
  }

  get playing(): boolean {
    return this.isPlaying;
  }

  get currentRecordingPath(): string | null {
    return this.recordingPath;
  }
}

// Singleton instance
export const audioService = new AudioService();