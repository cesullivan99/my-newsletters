import React, {useEffect} from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createStackNavigator} from '@react-navigation/stack';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import {StatusBar, StyleSheet, Linking} from 'react-native';

import AuthScreen from './components/AuthScreen';
import BriefingPlayer from './components/BriefingPlayer';
import VoiceInterface from './components/VoiceInterface';
import {AuthProvider, useAuth} from './services/auth';

export type RootStackParamList = {
  Auth: undefined;
  Briefing: {sessionId: string};
  Voice: {sessionId: string};
};

const Stack = createStackNavigator<RootStackParamList>();

const AppNavigator: React.FC = () => {
  const {isAuthenticated, isLoading} = useAuth();

  console.log('App state - isAuthenticated:', isAuthenticated, 'isLoading:', isLoading);

  if (isLoading) {
    return null; // Could add loading screen here
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerStyle: styles.header,
          headerTintColor: '#ffffff',
          headerTitleStyle: styles.headerTitle,
        }}>
        {!isAuthenticated ? (
          <Stack.Screen
            name="Auth"
            component={AuthScreen}
            options={{
              title: 'Newsletter Voice Assistant',
              headerShown: false,
            }}
          />
        ) : (
          <>
            <Stack.Screen
              name="Briefing"
              component={BriefingPlayer}
              options={{
                title: 'Daily Briefing',
                headerLeft: () => null,
              }}
            />
            <Stack.Screen
              name="Voice"
              component={VoiceInterface}
              options={{
                title: 'Voice Chat',
                presentation: 'modal',
              }}
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};

const App: React.FC = () => {
  useEffect(() => {
    const handleDeepLink = (url: string) => {
      console.log('Deep link received in App:', url);
      // The AuthProvider will handle this through its own Linking listener
    };

    // Handle deep link when app is already running
    const linkingListener = Linking.addEventListener('url', handleDeepLink);

    // Handle deep link when app is launched from deep link
    Linking.getInitialURL().then((url) => {
      if (url) {
        console.log('Initial URL:', url);
        handleDeepLink(url);
      }
    });

    return () => {
      linkingListener.remove();
    };
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" backgroundColor="#1a1a1a" />
      <AuthProvider>
        <AppNavigator />
      </AuthProvider>
    </SafeAreaProvider>
  );
};

const styles = StyleSheet.create({
  header: {
    backgroundColor: '#1a1a1a',
    elevation: 0,
    shadowOpacity: 0,
  },
  headerTitle: {
    fontWeight: '600',
    fontSize: 18,
  },
});

export default App;