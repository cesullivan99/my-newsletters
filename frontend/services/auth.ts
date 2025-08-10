import React, {createContext, useContext, useEffect, useState, ReactNode} from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {Linking, Alert} from 'react-native';
import {STORAGE_KEYS, API_CONFIG} from '../utils/constants';

export interface User {
  id: string;
  email: string;
  name: string;
  default_voice_type: string;
  default_playback_speed: number;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
}

export interface AuthContextType extends AuthState {
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({children}) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    token: null,
  });

  // Initialize auth state from storage
  useEffect(() => {
    initializeAuth();
  }, []);

  // Set up deep linking for OAuth callback
  useEffect(() => {
    const handleDeepLink = (url: string) => {
      handleOAuthCallback(url);
    };

    const linkingListener = Linking.addEventListener('url', (event) => {
      handleDeepLink(event.url);
    });

    return () => {
      linkingListener.remove();
    };
  }, []);

  const initializeAuth = async (): Promise<void> => {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      const userStr = await AsyncStorage.getItem(STORAGE_KEYS.USER_PREFERENCES);
      
      if (token && userStr) {
        const user = JSON.parse(userStr);
        
        // Validate token with backend
        const isValid = await validateToken(token);
        if (isValid) {
          setAuthState({
            user,
            isAuthenticated: true,
            isLoading: false,
            token,
          });
          return;
        }
      }

      // Clear invalid tokens
      await AsyncStorage.multiRemove([
        STORAGE_KEYS.AUTH_TOKEN,
        STORAGE_KEYS.USER_PREFERENCES,
      ]);
      
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        token: null,
      });
    } catch (error) {
      console.error('Error initializing auth:', error);
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        token: null,
      });
    }
  };

  const validateToken = async (token: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/auth/validate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      return response.ok;
    } catch (error) {
      console.error('Error validating token:', error);
      return false;
    }
  };

  const login = async (): Promise<void> => {
    try {
      setAuthState(prev => ({...prev, isLoading: true}));

      // Generate OAuth URL
      const authUrl = `${API_CONFIG.BASE_URL}/auth/gmail-oauth`;
      
      // Open OAuth flow in system browser
      const supported = await Linking.canOpenURL(authUrl);
      if (!supported) {
        throw new Error('Cannot open OAuth URL');
      }

      await Linking.openURL(authUrl);
    } catch (error) {
      console.error('Error starting login:', error);
      setAuthState(prev => ({...prev, isLoading: false}));
      Alert.alert('Login Error', 'Failed to start authentication process');
    }
  };

  const handleOAuthCallback = async (url: string): Promise<void> => {
    try {
      // Parse the callback URL for auth code/token
      const urlObj = new URL(url);
      const token = urlObj.searchParams.get('token');
      const error = urlObj.searchParams.get('error');

      if (error) {
        throw new Error(`OAuth error: ${error}`);
      }

      if (!token) {
        throw new Error('No token received from OAuth callback');
      }

      // Fetch user data with the token
      const response = await fetch(`${API_CONFIG.BASE_URL}/auth/user`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch user data');
      }

      const user: User = await response.json();

      // Store auth data
      await AsyncStorage.multiSet([
        [STORAGE_KEYS.AUTH_TOKEN, token],
        [STORAGE_KEYS.USER_PREFERENCES, JSON.stringify(user)],
      ]);

      setAuthState({
        user,
        isAuthenticated: true,
        isLoading: false,
        token,
      });
    } catch (error) {
      console.error('Error handling OAuth callback:', error);
      setAuthState(prev => ({...prev, isLoading: false}));
      Alert.alert('Authentication Error', 'Failed to complete login');
    }
  };

  const logout = async (): Promise<void> => {
    try {
      setAuthState(prev => ({...prev, isLoading: true}));

      // Revoke token on server
      if (authState.token) {
        await fetch(`${API_CONFIG.BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authState.token}`,
          },
        });
      }

      // Clear local storage
      await AsyncStorage.multiRemove([
        STORAGE_KEYS.AUTH_TOKEN,
        STORAGE_KEYS.USER_PREFERENCES,
        STORAGE_KEYS.CACHED_BRIEFINGS,
      ]);

      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        token: null,
      });
    } catch (error) {
      console.error('Error logging out:', error);
      // Force logout even if server call fails
      await AsyncStorage.multiRemove([
        STORAGE_KEYS.AUTH_TOKEN,
        STORAGE_KEYS.USER_PREFERENCES,
        STORAGE_KEYS.CACHED_BRIEFINGS,
      ]);

      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        token: null,
      });
    }
  };

  const refreshToken = async (): Promise<void> => {
    try {
      if (!authState.token) {
        throw new Error('No token to refresh');
      }

      const response = await fetch(`${API_CONFIG.BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authState.token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to refresh token');
      }

      const {token: newToken, user} = await response.json();

      await AsyncStorage.multiSet([
        [STORAGE_KEYS.AUTH_TOKEN, newToken],
        [STORAGE_KEYS.USER_PREFERENCES, JSON.stringify(user)],
      ]);

      setAuthState({
        user,
        isAuthenticated: true,
        isLoading: false,
        token: newToken,
      });
    } catch (error) {
      console.error('Error refreshing token:', error);
      // If refresh fails, logout user
      await logout();
    }
  };

  const contextValue: AuthContextType = {
    ...authState,
    login,
    logout,
    refreshToken,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// Token refresh helper for automatic renewal
export const setupTokenRefresh = (refreshCallback: () => Promise<void>) => {
  // Set up periodic token refresh (every 50 minutes)
  const refreshInterval = setInterval(() => {
    refreshCallback().catch(console.error);
  }, 50 * 60 * 1000);

  return () => clearInterval(refreshInterval);
};