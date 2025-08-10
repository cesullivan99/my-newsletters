import React, {useState, useEffect, useRef} from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ScrollView,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../App';
import {useAuth} from '../services/auth';
import {
  apiClient,
  BriefingResponse,
  Story,
  SessionState,
} from '../services/api';
import {audioService, PlaybackState} from '../services/audio';
import {UI_COLORS, BRIEFING_STATES} from '../utils/constants';

type BriefingPlayerNavigationProp = StackNavigationProp<
  RootStackParamList,
  'Briefing'
>;

interface Props {
  navigation: BriefingPlayerNavigationProp;
}

const BriefingPlayer: React.FC<Props> = ({navigation}) => {
  const {user, logout} = useAuth();
  
  // State
  const [briefingState, setBriefingState] = useState(BRIEFING_STATES.IDLE);
  const [currentSession, setCurrentSession] = useState<SessionState | null>(null);
  const [currentStory, setCurrentStory] = useState<Story | null>(null);
  const [playbackState, setPlaybackState] = useState<PlaybackState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Refs
  const sessionUpdateTimer = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (user) {
      initializeBriefing();
    }

    return () => {
      cleanup();
    };
  }, [user]);

  const initializeBriefing = async () => {
    try {
      setIsLoading(true);
      setError(null);
      setBriefingState(BRIEFING_STATES.LOADING);

      if (!user) {
        throw new Error('User not authenticated');
      }

      // Start new briefing session
      const briefingResponse: BriefingResponse = await apiClient.startBriefing({
        user_id: user.id,
        voice_type: user.default_voice_type,
      });

      // Get initial session state
      const sessionState = await apiClient.getSessionState(briefingResponse.session_id);
      setCurrentSession(sessionState);

      // Get first story
      const firstStory = await apiClient.getCurrentStory(briefingResponse.session_id);
      setCurrentStory(firstStory);

      setBriefingState(BRIEFING_STATES.IDLE);
      
      // Start periodic session state updates
      startSessionUpdates(briefingResponse.session_id);

    } catch (error) {
      console.error('Error initializing briefing:', error);
      setError('Failed to load your daily briefing');
      setBriefingState(BRIEFING_STATES.ERROR);
    } finally {
      setIsLoading(false);
    }
  };

  const startSessionUpdates = (sessionId: string) => {
    sessionUpdateTimer.current = setInterval(async () => {
      try {
        const sessionState = await apiClient.getSessionState(sessionId);
        setCurrentSession(sessionState);
        
        // Update current story if changed
        const story = await apiClient.getCurrentStory(sessionId);
        setCurrentStory(story);
      } catch (error) {
        console.error('Error updating session state:', error);
      }
    }, 5000); // Update every 5 seconds
  };

  const playBriefing = async () => {
    try {
      if (!currentStory?.audio_url || !currentSession) {
        Alert.alert('Error', 'No audio content available');
        return;
      }

      setBriefingState(BRIEFING_STATES.PLAYING);

      // Start audio playback with progress tracking
      await audioService.startPlayback(
        currentStory.audio_url,
        (state: PlaybackState) => {
          setPlaybackState(state);
          
          // Check if audio finished
          if (state.currentPositionSec >= state.currentDurationSec) {
            handleAudioFinished();
          }
        }
      );

    } catch (error) {
      console.error('Error starting playback:', error);
      setBriefingState(BRIEFING_STATES.ERROR);
      Alert.alert('Playback Error', 'Failed to play audio');
    }
  };

  const pauseBriefing = async () => {
    try {
      await audioService.pausePlayback();
      if (currentSession) {
        await apiClient.pauseBriefing(currentSession.session_id);
      }
      setBriefingState(BRIEFING_STATES.PAUSED);
    } catch (error) {
      console.error('Error pausing briefing:', error);
    }
  };

  const resumeBriefing = async () => {
    try {
      await audioService.resumePlayback();
      if (currentSession) {
        await apiClient.resumeBriefing(currentSession.session_id);
      }
      setBriefingState(BRIEFING_STATES.PLAYING);
    } catch (error) {
      console.error('Error resuming briefing:', error);
    }
  };

  const skipStory = async () => {
    try {
      if (!currentSession) return;

      setBriefingState(BRIEFING_STATES.LOADING);
      
      // Stop current playback
      await audioService.stopPlayback();
      
      // Skip to next story
      const nextStory = await apiClient.skipStory(currentSession.session_id);
      
      if (nextStory) {
        setCurrentStory(nextStory);
        setBriefingState(BRIEFING_STATES.IDLE);
      } else {
        // End of briefing
        setBriefingState(BRIEFING_STATES.COMPLETED);
        Alert.alert('Briefing Complete', 'You have finished all stories in your daily briefing!');
      }

    } catch (error) {
      console.error('Error skipping story:', error);
      setBriefingState(BRIEFING_STATES.ERROR);
      Alert.alert('Error', 'Failed to skip story');
    }
  };

  const getDetailedSummary = async () => {
    try {
      if (!currentSession) return;

      const detailedSummary = await apiClient.getDetailedSummary(currentSession.session_id);
      
      Alert.alert(
        'Full Story',
        detailedSummary,
        [
          {text: 'Close', style: 'default'},
          {text: 'Read with Voice', onPress: () => playDetailedSummary(detailedSummary)},
        ]
      );
    } catch (error) {
      console.error('Error getting detailed summary:', error);
      Alert.alert('Error', 'Failed to get story details');
    }
  };

  const playDetailedSummary = async (text: string) => {
    // This would need TTS implementation for reading the detailed summary
    Alert.alert('Feature Coming Soon', 'Voice reading of detailed summaries will be available soon.');
  };

  const openVoiceInterface = () => {
    if (!currentSession) {
      Alert.alert('Error', 'No active briefing session');
      return;
    }

    navigation.navigate('Voice', {sessionId: currentSession.session_id});
  };

  const handleAudioFinished = async () => {
    // Automatically advance to next story
    await skipStory();
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const cleanup = () => {
    if (sessionUpdateTimer.current) {
      clearInterval(sessionUpdateTimer.current);
    }
    audioService.cleanup();
  };

  const getProgressPercentage = (): number => {
    if (!playbackState || !currentSession) return 0;
    if (playbackState.currentDurationSec === 0) return 0;
    return (playbackState.currentPositionSec / playbackState.currentDurationSec) * 100;
  };

  const getSessionProgressText = (): string => {
    if (!currentSession) return '';
    return `Story ${currentSession.current_story_index + 1} of ${currentSession.total_stories}`;
  };

  if (isLoading && briefingState === BRIEFING_STATES.LOADING) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={UI_COLORS.PRIMARY} />
          <Text style={styles.loadingText}>Loading your daily briefing...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error && briefingState === BRIEFING_STATES.ERROR) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={initializeBriefing}>
            <Text style={styles.retryButtonText}>Try Again</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.logoutButton} onPress={logout}>
            <Text style={styles.logoutButtonText}>Logout</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.welcomeText}>Good morning, {user?.name}!</Text>
          <Text style={styles.sessionProgress}>{getSessionProgressText()}</Text>
        </View>

        {/* Current Story */}
        {currentStory && (
          <View style={styles.storyContainer}>
            <View style={styles.storyHeader}>
              <Text style={styles.newsletterName}>{currentStory.newsletter_name}</Text>
              <Text style={styles.publishedDate}>
                {new Date(currentStory.published_at).toLocaleDateString()}
              </Text>
            </View>
            
            <Text style={styles.storyHeadline}>{currentStory.headline}</Text>
            <Text style={styles.storySummary}>{currentStory.one_sentence_summary}</Text>
          </View>
        )}

        {/* Progress Bar */}
        {playbackState && (
          <View style={styles.progressContainer}>
            <View style={styles.progressBar}>
              <View 
                style={[
                  styles.progressFill, 
                  {width: `${getProgressPercentage()}%`}
                ]} 
              />
            </View>
            <View style={styles.progressTime}>
              <Text style={styles.timeText}>
                {formatTime(playbackState.currentPositionSec)}
              </Text>
              <Text style={styles.timeText}>
                {formatTime(playbackState.currentDurationSec)}
              </Text>
            </View>
          </View>
        )}

        {/* Control Buttons */}
        <View style={styles.controlsContainer}>
          <TouchableOpacity
            style={styles.controlButton}
            onPress={skipStory}
            disabled={briefingState === BRIEFING_STATES.LOADING}
          >
            <Text style={styles.controlButtonText}>Skip</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.playButton, briefingState === BRIEFING_STATES.PLAYING && styles.pauseButton]}
            onPress={
              briefingState === BRIEFING_STATES.PLAYING
                ? pauseBriefing
                : briefingState === BRIEFING_STATES.PAUSED
                ? resumeBriefing
                : playBriefing
            }
            disabled={briefingState === BRIEFING_STATES.LOADING}
          >
            <Text style={styles.playButtonText}>
              {briefingState === BRIEFING_STATES.PLAYING
                ? 'Pause'
                : briefingState === BRIEFING_STATES.PAUSED
                ? 'Resume'
                : 'Play'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.controlButton}
            onPress={getDetailedSummary}
            disabled={briefingState === BRIEFING_STATES.LOADING}
          >
            <Text style={styles.controlButtonText}>Details</Text>
          </TouchableOpacity>
        </View>

        {/* Voice Command Button */}
        <TouchableOpacity
          style={styles.voiceButton}
          onPress={openVoiceInterface}
          disabled={!currentSession}
        >
          <Text style={styles.voiceButtonText}>🎤 Voice Commands</Text>
        </TouchableOpacity>

        {/* Status */}
        <View style={styles.statusContainer}>
          <Text style={styles.statusText}>
            {briefingState === BRIEFING_STATES.PLAYING && 'Playing briefing...'}
            {briefingState === BRIEFING_STATES.PAUSED && 'Briefing paused'}
            {briefingState === BRIEFING_STATES.COMPLETED && 'Briefing completed!'}
            {briefingState === BRIEFING_STATES.IDLE && 'Ready to play'}
          </Text>
        </View>
      </ScrollView>

      {/* Settings/Logout */}
      <View style={styles.footer}>
        <TouchableOpacity style={styles.footerButton} onPress={logout}>
          <Text style={styles.footerButtonText}>Logout</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: UI_COLORS.DARK_BACKGROUND,
  },
  content: {
    padding: 24,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 16,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
    marginTop: 16,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  errorText: {
    fontSize: 16,
    color: UI_COLORS.ERROR,
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 24,
  },
  retryButton: {
    backgroundColor: UI_COLORS.PRIMARY,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  logoutButton: {
    backgroundColor: UI_COLORS.SECONDARY,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  logoutButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  header: {
    marginBottom: 32,
  },
  welcomeText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    marginBottom: 8,
  },
  sessionProgress: {
    fontSize: 16,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
  },
  storyContainer: {
    backgroundColor: UI_COLORS.DARK_SURFACE,
    padding: 20,
    borderRadius: 12,
    marginBottom: 24,
  },
  storyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  newsletterName: {
    fontSize: 14,
    fontWeight: '600',
    color: UI_COLORS.PRIMARY,
  },
  publishedDate: {
    fontSize: 12,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
  },
  storyHeadline: {
    fontSize: 18,
    fontWeight: '600',
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    marginBottom: 12,
    lineHeight: 24,
  },
  storySummary: {
    fontSize: 14,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
    lineHeight: 20,
  },
  progressContainer: {
    marginBottom: 32,
  },
  progressBar: {
    height: 4,
    backgroundColor: UI_COLORS.DARK_SURFACE,
    borderRadius: 2,
    marginBottom: 8,
  },
  progressFill: {
    height: '100%',
    backgroundColor: UI_COLORS.PRIMARY,
    borderRadius: 2,
  },
  progressTime: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  timeText: {
    fontSize: 12,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
  },
  controlsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    marginBottom: 32,
  },
  controlButton: {
    backgroundColor: UI_COLORS.SECONDARY,
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
    minWidth: 80,
    alignItems: 'center',
  },
  controlButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  playButton: {
    backgroundColor: UI_COLORS.PRIMARY,
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 12,
    minWidth: 120,
    alignItems: 'center',
  },
  pauseButton: {
    backgroundColor: UI_COLORS.WARNING,
  },
  playButtonText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  voiceButton: {
    backgroundColor: UI_COLORS.DARK_SURFACE,
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 24,
    borderWidth: 1,
    borderColor: UI_COLORS.PRIMARY,
  },
  voiceButtonText: {
    color: UI_COLORS.PRIMARY,
    fontSize: 16,
    fontWeight: '600',
  },
  statusContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  statusText: {
    fontSize: 14,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
    fontStyle: 'italic',
  },
  footer: {
    padding: 24,
    borderTopWidth: 1,
    borderTopColor: UI_COLORS.DARK_SURFACE,
  },
  footerButton: {
    backgroundColor: UI_COLORS.SECONDARY,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
  },
  footerButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default BriefingPlayer;