import React, {useState} from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import {useAuth} from '../services/auth';
import {UI_COLORS} from '../utils/constants';

const AuthScreen: React.FC = () => {
  const {login, isLoading} = useAuth();
  const [isConnecting, setIsConnecting] = useState(false);

  const handleLogin = async () => {
    try {
      setIsConnecting(true);
      await login();
    } catch (error) {
      console.error('Login error:', error);
      Alert.alert(
        'Authentication Error',
        'Failed to start the login process. Please try again.'
      );
    } finally {
      setIsConnecting(false);
    }
  };

  const showInfoAlert = () => {
    Alert.alert(
      'Newsletter Voice Assistant',
      'This app connects to your Gmail to find newsletters and creates personalized daily audio briefings. You can interrupt and ask questions during briefings using voice commands.\n\nWe only read newsletter emails and never access personal messages.',
      [
        {text: 'Learn More', onPress: () => {}},
        {text: 'OK', style: 'default'},
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={UI_COLORS.DARK_BACKGROUND} />
      
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Newsletter{'\n'}Voice Assistant</Text>
          <Text style={styles.subtitle}>
            Transform your newsletters into interactive daily briefings
          </Text>
        </View>

        <View style={styles.features}>
          <FeatureItem 
            icon="🎧"
            title="Audio Briefings"
            description="Listen to your newsletters as personalized daily briefings"
          />
          <FeatureItem 
            icon="💬"
            title="Voice Control"
            description="Skip stories, ask for details, or get more info with voice commands"
          />
          <FeatureItem 
            icon="📱"
            title="Smart Processing"
            description="AI extracts key stories and creates one-sentence summaries"
          />
        </View>

        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.loginButton, (isLoading || isConnecting) && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={isLoading || isConnecting}
          >
            {isLoading || isConnecting ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator color="#ffffff" size="small" />
                <Text style={styles.loadingText}>Connecting...</Text>
              </View>
            ) : (
              <Text style={styles.loginButtonText}>Connect Gmail Account</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity style={styles.infoButton} onPress={showInfoAlert}>
            <Text style={styles.infoButtonText}>How does this work?</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.footer}>
          <Text style={styles.privacyText}>
            Your privacy is protected. We only access newsletter emails and never read personal messages.
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
};

interface FeatureItemProps {
  icon: string;
  title: string;
  description: string;
}

const FeatureItem: React.FC<FeatureItemProps> = ({icon, title, description}) => (
  <View style={styles.featureItem}>
    <Text style={styles.featureIcon}>{icon}</Text>
    <View style={styles.featureContent}>
      <Text style={styles.featureTitle}>{title}</Text>
      <Text style={styles.featureDescription}>{description}</Text>
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: UI_COLORS.DARK_BACKGROUND,
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: 'space-between',
  },
  header: {
    marginTop: 60,
    alignItems: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    textAlign: 'center',
    lineHeight: 40,
    marginBottom: 16,
  },
  subtitle: {
    fontSize: 18,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
    textAlign: 'center',
    lineHeight: 24,
  },
  features: {
    marginVertical: 40,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
    paddingHorizontal: 8,
  },
  featureIcon: {
    fontSize: 32,
    marginRight: 16,
    width: 40,
    textAlign: 'center',
  },
  featureContent: {
    flex: 1,
  },
  featureTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    marginBottom: 4,
  },
  featureDescription: {
    fontSize: 14,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
    lineHeight: 20,
  },
  actions: {
    marginBottom: 40,
  },
  loginButton: {
    backgroundColor: UI_COLORS.PRIMARY,
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 16,
    elevation: 2,
    shadowColor: UI_COLORS.PRIMARY,
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },
  buttonDisabled: {
    backgroundColor: UI_COLORS.SECONDARY,
    shadowOpacity: 0,
    elevation: 0,
  },
  loginButtonText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '600',
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  loadingText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 12,
  },
  infoButton: {
    alignItems: 'center',
    paddingVertical: 12,
  },
  infoButtonText: {
    color: UI_COLORS.DARK_TEXT_SECONDARY,
    fontSize: 16,
    textDecorationLine: 'underline',
  },
  footer: {
    marginBottom: 20,
  },
  privacyText: {
    fontSize: 12,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
    textAlign: 'center',
    lineHeight: 18,
    opacity: 0.8,
  },
});

export default AuthScreen;