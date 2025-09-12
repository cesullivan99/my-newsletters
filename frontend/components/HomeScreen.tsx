import React, {useState, useEffect} from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../App';
import {useAuth} from '../services/auth';
import {apiClient} from '../services/api';
import {UI_COLORS} from '../utils/constants';

type HomeScreenNavigationProp = StackNavigationProp<
  RootStackParamList,
  'Home'
>;

interface Props {
  navigation: HomeScreenNavigationProp;
}

const HomeScreen: React.FC<Props> = ({navigation}) => {
  const {user, logout} = useAuth();
  
  // State
  const [isFetchingNewsletters, setIsFetchingNewsletters] = useState(false);
  const [isCheckingStories, setIsCheckingStories] = useState(false);
  const [hasStories, setHasStories] = useState(false);
  const [newsletterCount, setNewsletterCount] = useState(0);
  const [storyCount, setStoryCount] = useState(0);

  useEffect(() => {
    checkForExistingStories();
  }, []);

  const checkForExistingStories = async () => {
    try {
      setIsCheckingStories(true);
      
      // Check if user has any stories available
      const response = await apiClient.checkUserStories(user?.id);
      setHasStories(response.has_stories);
      setStoryCount(response.story_count || 0);
      setNewsletterCount(response.newsletter_count || 0);
    } catch (error) {
      console.error('Error checking for stories:', error);
    } finally {
      setIsCheckingStories(false);
    }
  };

  const fetchNewsletters = async () => {
    try {
      setIsFetchingNewsletters(true);
      
      // Call the newsletter fetch endpoint
      const response = await apiClient.fetchNewsletters();
      
      if (response.newsletters_fetched > 0) {
        Alert.alert(
          'Success!', 
          `Fetched ${response.newsletters_fetched} newsletters from Gmail`,
          [
            {text: 'OK', onPress: () => checkForExistingStories()}
          ]
        );
      } else {
        Alert.alert(
          'No Newsletters Found',
          'No newsletters were found in your Gmail. Make sure you have newsletters in your inbox from the last 7 days.',
        );
      }
    } catch (error: any) {
      console.error('Error fetching newsletters:', error);
      
      if (error.response?.data?.error === 'no_gmail_auth') {
        Alert.alert(
          'Gmail Authentication Required',
          'Please re-authenticate with Gmail to fetch newsletters.',
          [
            {text: 'Cancel', style: 'cancel'},
            {text: 'Re-authenticate', onPress: () => logout()}
          ]
        );
      } else {
        Alert.alert('Error', 'Failed to fetch newsletters. Please try again.');
      }
    } finally {
      setIsFetchingNewsletters(false);
    }
  };

  const startBriefing = async () => {
    if (!hasStories) {
      Alert.alert(
        'No Stories Available',
        'Please fetch newsletters from Gmail first to create your briefing.',
        [
          {text: 'Cancel', style: 'cancel'},
          {text: 'Fetch Now', onPress: fetchNewsletters}
        ]
      );
      return;
    }

    // Navigate to the briefing player
    navigation.navigate('Briefing');
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.welcomeText}>Welcome, {user?.name}!</Text>
          <Text style={styles.subtitle}>Your Daily Newsletter Briefing</Text>
        </View>

        {/* Status Card */}
        <View style={styles.statusCard}>
          <Text style={styles.statusTitle}>Current Status</Text>
          {isCheckingStories ? (
            <ActivityIndicator size="small" color={UI_COLORS.PRIMARY} />
          ) : (
            <>
              <View style={styles.statusRow}>
                <Text style={styles.statusLabel}>Newsletters:</Text>
                <Text style={styles.statusValue}>{newsletterCount}</Text>
              </View>
              <View style={styles.statusRow}>
                <Text style={styles.statusLabel}>Stories:</Text>
                <Text style={styles.statusValue}>{storyCount}</Text>
              </View>
              {!hasStories && (
                <Text style={styles.statusMessage}>
                  Fetch newsletters to get started
                </Text>
              )}
            </>
          )}
        </View>

        {/* Main Actions */}
        <View style={styles.actionsContainer}>
          {/* Fetch Newsletters Button */}
          <TouchableOpacity
            style={[
              styles.actionButton,
              styles.fetchButton,
              isFetchingNewsletters && styles.buttonDisabled
            ]}
            onPress={fetchNewsletters}
            disabled={isFetchingNewsletters}
          >
            {isFetchingNewsletters ? (
              <ActivityIndicator size="small" color="#ffffff" />
            ) : (
              <>
                <Text style={styles.actionButtonIcon}>📧</Text>
                <Text style={styles.actionButtonTitle}>Fetch Newsletters</Text>
                <Text style={styles.actionButtonSubtitle}>
                  Get latest from Gmail
                </Text>
              </>
            )}
          </TouchableOpacity>

          {/* Play Briefing Button */}
          <TouchableOpacity
            style={[
              styles.actionButton,
              styles.playButton,
              !hasStories && styles.buttonDisabled
            ]}
            onPress={startBriefing}
            disabled={!hasStories || isCheckingStories}
          >
            {isCheckingStories ? (
              <ActivityIndicator size="small" color="#ffffff" />
            ) : (
              <>
                <Text style={styles.actionButtonIcon}>🎧</Text>
                <Text style={styles.actionButtonTitle}>Play Briefing</Text>
                <Text style={styles.actionButtonSubtitle}>
                  {hasStories ? `${storyCount} stories ready` : 'No stories available'}
                </Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        {/* Instructions */}
        {!hasStories && (
          <View style={styles.instructionsContainer}>
            <Text style={styles.instructionsTitle}>Getting Started</Text>
            <Text style={styles.instructionsText}>
              1. Tap "Fetch Newsletters" to import your newsletters from Gmail
            </Text>
            <Text style={styles.instructionsText}>
              2. Once fetched, tap "Play Briefing" to listen to your personalized news
            </Text>
            <Text style={styles.instructionsText}>
              3. Use voice commands to control playback
            </Text>
          </View>
        )}

        {/* Footer */}
        <View style={styles.footer}>
          <TouchableOpacity style={styles.logoutButton} onPress={logout}>
            <Text style={styles.logoutButtonText}>Logout</Text>
          </TouchableOpacity>
        </View>
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
    flex: 1,
    padding: 24,
  },
  header: {
    marginBottom: 32,
  },
  welcomeText: {
    fontSize: 28,
    fontWeight: 'bold',
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
  },
  statusCard: {
    backgroundColor: UI_COLORS.DARK_SURFACE,
    padding: 20,
    borderRadius: 12,
    marginBottom: 32,
  },
  statusTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    marginBottom: 16,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  statusLabel: {
    fontSize: 14,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
  },
  statusValue: {
    fontSize: 14,
    fontWeight: '600',
    color: UI_COLORS.DARK_TEXT_PRIMARY,
  },
  statusMessage: {
    fontSize: 12,
    color: UI_COLORS.WARNING,
    marginTop: 8,
    fontStyle: 'italic',
  },
  actionsContainer: {
    marginBottom: 32,
  },
  actionButton: {
    padding: 24,
    borderRadius: 16,
    marginBottom: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  fetchButton: {
    backgroundColor: UI_COLORS.SECONDARY,
  },
  playButton: {
    backgroundColor: UI_COLORS.PRIMARY,
  },
  buttonDisabled: {
    opacity: 0.5,
    backgroundColor: UI_COLORS.DARK_SURFACE,
  },
  actionButtonIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  actionButtonTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4,
  },
  actionButtonSubtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  instructionsContainer: {
    backgroundColor: UI_COLORS.DARK_SURFACE,
    padding: 20,
    borderRadius: 12,
    marginBottom: 32,
  },
  instructionsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: UI_COLORS.DARK_TEXT_PRIMARY,
    marginBottom: 12,
  },
  instructionsText: {
    fontSize: 14,
    color: UI_COLORS.DARK_TEXT_SECONDARY,
    marginBottom: 8,
    lineHeight: 20,
  },
  footer: {
    marginTop: 'auto',
  },
  logoutButton: {
    backgroundColor: UI_COLORS.SECONDARY,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
  },
  logoutButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default HomeScreen;