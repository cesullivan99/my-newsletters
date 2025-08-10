import React, {useState, useEffect, useRef} from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Animated,
  Dimensions,
} from 'react-native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RouteProp} from '@react-navigation/native';
import {RootStackParamList} from '../App';
import {audioService, RecordingState} from '../services/audio';
import {VoiceWebSocket} from '../services/api';
import {UI_COLORS, BRIEFING_STATES, VOICE_CONFIG} from '../utils/constants';

type VoiceInterfaceNavigationProp = StackNavigationProp<
  RootStackParamList,
  'Voice'
>;
type VoiceInterfaceRouteProp = RouteProp<RootStackParamList, 'Voice'>;

interface Props {
  navigation: VoiceInterfaceNavigationProp;
  route: VoiceInterfaceRouteProp;
}

const VoiceInterface: React.FC<Props> = ({navigation, route}) => {
  const {sessionId} = route.params;
  
  // State
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [responseText, setResponseText] = useState('');
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Refs
  const webSocket = useRef<VoiceWebSocket | null>(null);
  const pulseAnimation = useRef(new Animated.Value(0)).current;
  const recordingTimer = useRef<NodeJS.Timeout | null>(null);
  const audioLevelTimer = useRef<NodeJS.Timeout | null>(null);

  const {width} = Dimensions.get('window');

  useEffect(() => {
    setupWebSocketConnection();
    return () => {
      cleanup();
    };
  }, [sessionId]);

  // Pulse animation for recording state
  useEffect(() => {
    if (isRecording) {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnimation, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnimation, {
            toValue: 0,
            duration: 1000,
            useNativeDriver: true,
          }),
        ])
      );
      pulse.start();
    } else {
      pulseAnimation.stopAnimation();
      pulseAnimation.setValue(0);
    }
  }, [isRecording, pulseAnimation]);

  const setupWebSocketConnection = () => {
    try {
      webSocket.current = new VoiceWebSocket(sessionId);
      
      webSocket.current.connect(
        (data) => handleWebSocketMessage(data),
        (error) => handleWebSocketError(error)
      );

      // Check connection status
      setTimeout(() => {
        if (webSocket.current?.isConnected) {
          setIsConnected(true);
          setConnectionError(null);
        } else {
          setConnectionError('Failed to connect to voice service');
        }
      }, 3000);
    } catch (error) {
      console.error('Error setting up WebSocket:', error);
      setConnectionError('Connection setup failed');
    }
  };

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'response':
        setResponseText(data.text);
        break;
      case 'audio_response':
        // Handle audio response from server
        playAudioResponse(data.audio);
        break;
      case 'session_update':
        // Session state updated, might need to refresh briefing
        break;
      case 'error':
        Alert.alert('Voice Error', data.message);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const handleWebSocketError = (error: Event) => {
    console.error('WebSocket error:', error);
    setIsConnected(false);
    setConnectionError('Voice connection lost');
  };

  const playAudioResponse = async (audioData: string) => {
    try {
      // Convert base64 audio data to playable format
      // This would need proper implementation based on audio format
      console.log('Playing audio response:', audioData.length);
    } catch (error) {
      console.error('Error playing audio response:', error);
    }
  };

  const startRecording = async () => {
    try {
      if (!isConnected) {
        Alert.alert('Connection Error', 'Voice service is not connected');
        return;
      }

      setIsRecording(true);
      setRecordingTime(0);
      setResponseText('');

      const recordingPath = await audioService.startRecording(
        undefined,
        (state: RecordingState) => {
          setRecordingTime(state.recordSecs);
        }
      );

      // Start recording timer
      recordingTimer.current = setInterval(() => {
        if (recordingTime >= VOICE_CONFIG.MAX_RECORDING_DURATION) {
          stopRecording();
        }
      }, 1000);

      // Start audio level monitoring
      startAudioLevelMonitoring();

      console.log('Recording started:', recordingPath);
    } catch (error) {
      console.error('Error starting recording:', error);
      Alert.alert('Recording Error', 'Failed to start voice recording');
      setIsRecording(false);
    }
  };

  const stopRecording = async () => {
    try {
      if (!isRecording) return;

      setIsRecording(false);
      
      if (recordingTimer.current) {
        clearInterval(recordingTimer.current);
        recordingTimer.current = null;
      }

      if (audioLevelTimer.current) {
        clearInterval(audioLevelTimer.current);
        audioLevelTimer.current = null;
      }

      const recordingPath = await audioService.stopRecording();
      
      // Check minimum recording duration
      if (recordingTime < VOICE_CONFIG.MIN_RECORDING_DURATION) {
        Alert.alert('Recording too short', 'Please record for at least 0.5 seconds');
        return;
      }

      // Send audio to WebSocket
      await sendAudioToServer(recordingPath);

    } catch (error) {
      console.error('Error stopping recording:', error);
      Alert.alert('Recording Error', 'Failed to process voice recording');
    }
  };

  const sendAudioToServer = async (recordingPath: string) => {
    try {
      const audioBase64 = await audioService.audioFileToBase64(recordingPath);
      const audioBuffer = audioService.base64ToArrayBuffer(audioBase64);
      
      webSocket.current?.sendAudioData(audioBuffer);
      
      // Show processing state
      setResponseText('Processing your voice command...');
    } catch (error) {
      console.error('Error sending audio to server:', error);
      Alert.alert('Upload Error', 'Failed to send voice recording');
    }
  };

  const startAudioLevelMonitoring = () => {
    audioLevelTimer.current = setInterval(async () => {
      const level = await audioService.getAudioLevel();
      setAudioLevel(level);
    }, 100);
  };

  const cleanup = () => {
    if (recordingTimer.current) {
      clearInterval(recordingTimer.current);
    }
    if (audioLevelTimer.current) {
      clearInterval(audioLevelTimer.current);
    }
    if (webSocket.current) {
      webSocket.current.close();
    }
    audioService.cleanup();
  };

  const retryConnection = () => {
    setConnectionError(null);
    setupWebSocketConnection();
  };

  const goBack = () => {
    navigation.goBack();
  };

  const recordButtonScale = pulseAnimation.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1.2],
  });

  const recordButtonOpacity = pulseAnimation.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 0.7],
  });

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Voice Command</Text>
        <Text style={styles.subtitle}>
          {isConnected ? 'Ready to listen' : 'Connecting...'}
        </Text>
      </View>

      {connectionError && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{connectionError}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={retryConnection}>
            <Text style={styles.retryButtonText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      <View style={styles.visualizer}>
        {isRecording && (
          <View style={styles.audioLevelContainer}>
            <View 
              style={[
                styles.audioLevelBar,
                {height: Math.max(4, audioLevel * 2)}
              ]} 
            />
          </View>
        )}
      </View>

      <View style={styles.recordingContainer}>
        <Animated.View
          style={[
            styles.recordButton,
            isRecording && styles.recordButtonActive,
            {
              transform: [{scale: recordButtonScale}],
              opacity: recordButtonOpacity,
            },
          ]}
        >
          <TouchableOpacity
            style={styles.recordButtonInner}
            onPress={isRecording ? stopRecording : startRecording}
            disabled={!isConnected}
          >
            <View style={[
              styles.recordButtonIcon,
              isRecording ? styles.recordButtonIconActive : styles.recordButtonIconInactive
            ]} />
          </TouchableOpacity>
        </Animated.View>
        
        {isRecording && (
          <Text style={styles.recordingTime}>
            {Math.floor(recordingTime / 1000)}s
          </Text>
        )}
      </View>

      <View style={styles.responseContainer}>
        {responseText ? (
          <Text style={styles.responseText}>{responseText}</Text>
        ) : (
          <Text style={styles.instructionText}>
            {isRecording 
              ? 'Listening... Tap to stop' 
              : 'Tap to speak your command'
            }
          </Text>
        )}
      </View>

      <View style={styles.commandHints}>
        <Text style={styles.hintsTitle}>Voice Commands:</Text>
        <Text style={styles.hintText}>• "Skip" or "Next" - Skip current story</Text>
        <Text style={styles.hintText}>• "Tell me more" - Get full story details</Text>
        <Text style={styles.hintText}>• "What newsletter is this from?" - Get source info</Text>
        <Text style={styles.hintText}>• Ask any question about the story</Text>
      </View>

      <TouchableOpacity style={styles.backButton} onPress={goBack}>
        <Text style={styles.backButtonText}>Back to Briefing</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: UI_COLORS.DARK_BACKGROUND,
    paddingHorizontal: 24,
    paddingVertical: 20,
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
  },
  errorContainer: {
    backgroundColor: UI_COLORS.ERROR,
    padding: 16,
    borderRadius: 8,
    marginBottom: 20,
    alignItems: 'center',
  },
  errorText: {
    color: '#ffffff',
    fontSize: 14,
    marginBottom: 8,
    textAlign: 'center',
  },
  retryButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 4,
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  visualizer: {
    height: 60,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 40,
  },
  audioLevelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 40,
  },
  audioLevelBar: {
    width: 4,
    backgroundColor: UI_COLORS.PRIMARY,
    borderRadius: 2,
    marginHorizontal: 1,
  },
  recordingContainer: {
    alignItems: 'center',
    marginBottom: 40,
  },
  recordButton: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: UI_COLORS.PRIMARY,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: UI_COLORS.PRIMARY,
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  recordButtonActive: {
    backgroundColor: UI_COLORS.ERROR,
    shadowColor: UI_COLORS.ERROR,
  },
  recordButtonInner: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: 'center',
    alignItems: 'center',
  },
  recordButtonIcon: {
    borderRadius: 8,
  },
  recordButtonIconInactive: {
    width: 24,
    height: 24,
    backgroundColor: '#ffffff',
    borderRadius: 12,
  },
  recordButtonIconActive: {
    width: 16,
    height: 16,
    backgroundColor: '#ffffff',
  },
  recordingTime: {
    fontSize: 18,
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    fontWeight: '600',
    marginTop: 16,
  },
  responseContainer: {
    backgroundColor: UI_COLORS.DARK_SURFACE,
    padding: 20,
    borderRadius: 12,
    marginBottom: 40,
    minHeight: 80,
    justifyContent: 'center',
  },
  responseText: {
    fontSize: 16,
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    lineHeight: 24,
    textAlign: 'center',
  },
  instructionText: {
    fontSize: 16,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
    lineHeight: 24,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  commandHints: {
    marginBottom: 40,
  },
  hintsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    marginBottom: 12,
  },
  hintText: {
    fontSize: 14,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
    lineHeight: 20,
    marginBottom: 4,
  },
  backButton: {
    backgroundColor: UI_COLORS.SECONDARY,
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
  },
  backButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default VoiceInterface;