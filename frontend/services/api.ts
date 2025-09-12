import axios, {AxiosInstance, AxiosResponse} from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {API_CONFIG, STORAGE_KEYS} from '../utils/constants';

export interface BriefingRequest {
  user_id: string;
  voice_type?: string;
}

export interface BriefingResponse {
  session_id: string;
  first_story: string;
  total_stories: number;
}

export interface Story {
  id: string;
  headline: string;
  one_sentence_summary: string;
  full_text_summary: string;
  audio_url: string;
  newsletter_name: string;
  published_at: string;
}

export interface SessionState {
  session_id: string;
  current_story_id: string;
  current_story_index: number;
  session_status: 'playing' | 'paused' | 'completed';
  total_stories: number;
}

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      async config => {
        const token = await AsyncStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      error => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      response => response,
      async error => {
        if (error.response?.status === 401) {
          // Token expired, clear storage and redirect to auth
          await AsyncStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
          // Handle auth redirect in app
        }
        return Promise.reject(error);
      }
    );
  }

  async startBriefing(request: BriefingRequest): Promise<BriefingResponse> {
    const response: AxiosResponse<BriefingResponse> = await this.client.post(
      '/start-briefing',
      request
    );
    return response.data;
  }

  async getSessionState(sessionId: string): Promise<SessionState> {
    const response: AxiosResponse<SessionState> = await this.client.get(
      `/briefing/${sessionId}/state`
    );
    return response.data;
  }

  async getCurrentStory(sessionId: string): Promise<Story> {
    const response: AxiosResponse<Story> = await this.client.get(
      `/briefing/${sessionId}/current-story`
    );
    return response.data;
  }

  async pauseBriefing(sessionId: string): Promise<void> {
    await this.client.post(`/briefing/${sessionId}/pause`);
  }

  async resumeBriefing(sessionId: string): Promise<void> {
    await this.client.post(`/briefing/${sessionId}/resume`);
  }

  async skipStory(sessionId: string): Promise<Story | null> {
    const response: AxiosResponse<{next_story: Story | null}> = 
      await this.client.post(`/briefing/${sessionId}/skip`);
    return response.data.next_story;
  }

  async getDetailedSummary(sessionId: string): Promise<string> {
    const response: AxiosResponse<{detailed_summary: string}> = 
      await this.client.get(`/briefing/${sessionId}/detailed-summary`);
    return response.data.detailed_summary;
  }

  async getUserNewsletters(userId: string): Promise<any[]> {
    const response: AxiosResponse<{newsletters: any[]}> = 
      await this.client.get(`/users/${userId}/newsletters`);
    return response.data.newsletters;
  }

  async updateUserPreferences(
    userId: string, 
    preferences: Record<string, any>
  ): Promise<void> {
    await this.client.put(`/users/${userId}/preferences`, preferences);
  }

  async fetchNewsletters(): Promise<{newsletters_fetched: number; status: string}> {
    const response: AxiosResponse<{newsletters_fetched: number; status: string}> = 
      await this.client.post('/newsletters/fetch');
    return response.data;
  }

  async checkUserStories(userId?: string): Promise<{
    has_stories: boolean;
    story_count: number;
    newsletter_count: number;
  }> {
    const response: AxiosResponse<{
      has_stories: boolean;
      story_count: number;
      newsletter_count: number;
    }> = await this.client.get('/user/stories-status');
    return response.data;
  }

  // WebSocket connection helper
  createWebSocketConnection(sessionId: string): WebSocket {
    const wsUrl = `${API_CONFIG.WEBSOCKET_URL}/voice-stream/${sessionId}`;
    return new WebSocket(wsUrl);
  }
}

export const apiClient = new APIClient();

// WebSocket utilities
export class VoiceWebSocket {
  private ws: WebSocket | null = null;
  private sessionId: string;
  
  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  connect(onMessage: (data: any) => void, onError: (error: Event) => void): void {
    this.ws = apiClient.createWebSocketConnection(this.sessionId);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected for session:', this.sessionId);
    };
    
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
    
    this.ws.onerror = onError;
    
    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
    };
  }

  sendAudioData(audioData: ArrayBuffer): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(audioData);
    }
  }

  sendTextMessage(message: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'text',
        content: message,
      }));
    }
  }

  close(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}