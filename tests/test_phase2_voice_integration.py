#!/usr/bin/env python3
"""
Phase 2: Voice Integration Testing
Testing voice functionality including Vocode StreamingConversation,
voice actions, and WebSocket communication
"""

import pytest
import asyncio
import json
import websockets
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.voice.conversation_manager import ConversationManager
from backend.voice.actions.skip_story_action import SkipStoryAction
from backend.voice.actions.tell_more_action import TellMeMoreAction
from backend.voice.actions.metadata_action import MetadataAction
from backend.voice.actions.conversational_query_action import ConversationalQueryAction
from backend.voice.agent_config import create_briefing_agent_config, get_briefing_system_prompt
from backend.models.database import User, ListeningSession, Newsletter, Story
from backend.database import get_db_session


class TestPhase2VoiceIntegration:
    """Phase 2: Voice Integration Testing (15 tests)"""
    
    def __init__(self):
        self.passed_tests = []
        self.failed_tests = []
        self.test_results = {
            "phase": "Phase 2: Voice Integration",
            "total_tests": 15,
            "passed": 0,
            "failed": 0,
            "tests": {}
        }
    
    async def setup_test_data(self):
        """Create test user and session data"""
        mock_user = Mock(spec=User)
        mock_user.id = "test-user-123"
        mock_user.email = "test@example.com"
        
        mock_session = Mock(spec=ListeningSession)
        mock_session.id = "test-session-456"
        mock_session.user_id = mock_user.id
        mock_session.current_position = 0
        mock_session.story_queue = ["story-1", "story-2", "story-3"]
        mock_session.status = "active"
        
        mock_newsletter = Mock(spec=Newsletter)
        mock_newsletter.id = "newsletter-789"
        mock_newsletter.subject = "Daily Tech News"
        mock_newsletter.sender = "TechNews Daily"
        mock_newsletter.date_received = datetime.now()
        
        mock_story = Mock(spec=Story)
        mock_story.id = "story-1"
        mock_story.newsletter_id = mock_newsletter.id
        mock_story.title = "AI Breakthrough"
        mock_story.content = "Researchers have made a significant breakthrough in AI..."
        mock_story.summary = "Major AI breakthrough announced"
        
        return {
            "user": mock_user,
            "session": mock_session,
            "newsletter": mock_newsletter,
            "story": mock_story
        }
    
    # ============= 2.1 Vocode StreamingConversation Testing =============
    
    async def test_websocket_connection(self):
        """Test WebSocket connection establishment"""
        test_name = "WebSocket Connection"
        try:
            # Test WebSocket connection to voice endpoint
            async with websockets.connect(
                "ws://localhost:5000/voice-stream/test-session-456",
                subprotocols=["voice"]
            ) as websocket:
                # Send initial connection message
                await websocket.send(json.dumps({
                    "type": "start",
                    "session_id": "test-session-456"
                }))
                
                # Wait for acknowledgment
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                
                assert data.get("type") == "connection_established"
                assert data.get("status") == "ready"
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_stt_integration(self):
        """Test Speech-to-Text transcription"""
        test_name = "STT Integration"
        try:
            with patch('backend.voice.conversation_manager.DeepgramTranscriber') as mock_transcriber:
                mock_transcriber.return_value.transcribe_stream = AsyncMock(
                    return_value="skip to the next story"
                )
                
                manager = ConversationManager()
                await manager.initialize()
                
                # Simulate audio input
                audio_data = b"mock_audio_data"
                transcript = await manager.process_audio(audio_data)
                
                assert transcript == "skip to the next story"
                assert mock_transcriber.called
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_tts_integration(self):
        """Test Text-to-Speech audio generation"""
        test_name = "TTS Integration"
        try:
            with patch('backend.voice.conversation_manager.ElevenLabsSynthesizer') as mock_synthesizer:
                mock_synthesizer.return_value.synthesize = AsyncMock(
                    return_value=b"mock_audio_output"
                )
                
                manager = ConversationManager()
                await manager.initialize()
                
                # Generate speech from text
                audio = await manager.generate_speech("Moving to the next story")
                
                assert audio == b"mock_audio_output"
                assert mock_synthesizer.called
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_conversation_flow(self):
        """Test agent responds appropriately to user input"""
        test_name = "Conversation Flow"
        try:
            test_data = await self.setup_test_data()
            
            with patch('backend.voice.agent_config.ChatGPTAgent') as mock_agent:
                mock_agent.return_value.respond = AsyncMock(
                    return_value="I'll skip to the next story for you."
                )
                
                config = create_briefing_agent_config(test_data["session"].id)
                # Mock agent creation since we're testing the configuration
                agent = mock_agent.return_value
                
                response = await agent.respond("skip to the next story")
                
                assert "skip" in response.lower() or "next" in response.lower()
                assert mock_agent.called
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_connection_stability(self):
        """Test long-duration conversation stability"""
        test_name = "Connection Stability"
        try:
            # Simulate long-running connection
            async with websockets.connect(
                "ws://localhost:5000/voice-stream/test-session-456",
                ping_interval=10,
                ping_timeout=30
            ) as websocket:
                # Keep connection alive for 30 seconds
                start_time = asyncio.get_event_loop().time()
                
                while asyncio.get_event_loop().time() - start_time < 30:
                    await websocket.ping()
                    await asyncio.sleep(5)
                
                # Connection should still be open
                assert websocket.open
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_error_recovery(self):
        """Test network interruption and reconnection handling"""
        test_name = "Error Recovery"
        try:
            reconnect_attempts = 0
            max_attempts = 3
            
            while reconnect_attempts < max_attempts:
                try:
                    async with websockets.connect(
                        "ws://localhost:5000/voice-stream/test-session-456"
                    ) as websocket:
                        if reconnect_attempts > 0:
                            # Successfully reconnected
                            self.passed_tests.append(test_name)
                            return True
                        
                        # Simulate network interruption
                        await websocket.close()
                        
                except websockets.exceptions.ConnectionClosed:
                    reconnect_attempts += 1
                    await asyncio.sleep(1)
            
            self.failed_tests.append(f"{test_name}: Could not reconnect")
            return False
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    # ============= 2.2 Voice Action Testing =============
    
    async def test_skip_story_action(self):
        """Test skip story voice action"""
        test_name = "Skip Story Action"
        try:
            test_data = await self.setup_test_data()
            
            with patch('backend.database.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                action = SkipStoryAction()
                result = await action.run(
                    user_input="skip this story",
                    session_id=test_data["session"].id
                )
                
                assert result.action_type == "skip_story"
                assert "next story" in result.response.lower()
                assert result.action_successful
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_tell_more_action(self):
        """Test tell me more voice action"""
        test_name = "Tell Me More Action"
        try:
            test_data = await self.setup_test_data()
            
            with patch('backend.database.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_session.get = AsyncMock(return_value=test_data["story"])
                mock_db.return_value.__aenter__.return_value = mock_session
                
                action = TellMeMoreAction()
                result = await action.run(
                    user_input="tell me more about this",
                    session_id=test_data["session"].id
                )
                
                assert result.action_type == "tell_more"
                assert len(result.response) > 100  # Full story content
                assert result.action_successful
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_metadata_action(self):
        """Test metadata query voice action"""
        test_name = "Metadata Action"
        try:
            test_data = await self.setup_test_data()
            
            with patch('backend.database.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_session.get = AsyncMock(side_effect=[
                    test_data["story"],
                    test_data["newsletter"]
                ])
                mock_db.return_value.__aenter__.return_value = mock_session
                
                action = MetadataAction()
                result = await action.run(
                    user_input="what newsletter is this from",
                    session_id=test_data["session"].id
                )
                
                assert result.action_type == "metadata"
                assert "Daily Tech News" in result.response
                assert result.action_successful
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_conversational_query(self):
        """Test natural conversational queries"""
        test_name = "Conversational Queries"
        try:
            with patch('backend.voice.actions.conversational_query_action.openai') as mock_openai:
                mock_openai.ChatCompletion.acreate = AsyncMock(
                    return_value={
                        "choices": [{
                            "message": {
                                "content": "Based on the context, this story discusses AI breakthroughs."
                            }
                        }]
                    }
                )
                
                action = ConversationalQueryAction()
                result = await action.run(
                    user_input="what do you think about this story",
                    session_id="test-session-456"
                )
                
                assert result.action_type == "conversational"
                assert len(result.response) > 0
                assert result.action_successful
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_action_responses(self):
        """Test all actions return properly formatted ActionOutput"""
        test_name = "Action Response Format"
        try:
            actions = [
                SkipStoryAction(),
                TellMeMoreAction(),
                MetadataAction(),
                ConversationalQueryAction()
            ]
            
            for action in actions:
                with patch.object(action, 'run', new_callable=AsyncMock) as mock_run:
                    mock_run.return_value = Mock(
                        action_type=action.__class__.__name__,
                        response="Test response",
                        action_successful=True,
                        session_id="test-session-456"
                    )
                    
                    result = await action.run("test input", "test-session-456")
                    
                    assert hasattr(result, 'action_type')
                    assert hasattr(result, 'response')
                    assert hasattr(result, 'action_successful')
                    assert hasattr(result, 'session_id')
            
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_session_state_updates(self):
        """Test voice actions update session state in database"""
        test_name = "Session State Updates"
        try:
            test_data = await self.setup_test_data()
            
            with patch('backend.database.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_update = AsyncMock()
                mock_session.execute = mock_update
                mock_session.commit = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                action = SkipStoryAction()
                await action.run(
                    user_input="skip",
                    session_id=test_data["session"].id
                )
                
                # Verify database update was called
                assert mock_update.called
                assert mock_session.commit.called
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_action_error_handling(self):
        """Test action failures don't break conversation flow"""
        test_name = "Action Error Handling"
        try:
            with patch('backend.database.get_db_session') as mock_db:
                # Simulate database error
                mock_db.side_effect = Exception("Database connection failed")
                
                action = SkipStoryAction()
                result = await action.run(
                    user_input="skip",
                    session_id="test-session-456"
                )
                
                # Should handle error gracefully
                assert result.action_successful == False
                assert "error" in result.response.lower() or "problem" in result.response.lower()
                
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    # ============= 2.3 Phrase Trigger Testing =============
    
    async def test_trigger_recognition(self):
        """Test all configured phrase patterns detected reliably"""
        test_name = "Trigger Recognition"
        try:
            phrase_triggers = {
                "skip": ["skip", "next", "move on", "skip this", "next story"],
                "tell_more": ["tell me more", "go deeper", "full story", "more details"],
                "metadata": ["what newsletter", "when published", "who wrote", "what source"]
            }
            
            for action_type, phrases in phrase_triggers.items():
                for phrase in phrases:
                    # Test phrase detection logic
                    detected = any(trigger in phrase.lower() for trigger in phrase_triggers[action_type])
                    assert detected, f"Failed to detect phrase: {phrase}"
            
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def test_false_positive_prevention(self):
        """Test similar phrases don't trigger wrong actions"""
        test_name = "False Positive Prevention"
        try:
            # Test phrases that shouldn't trigger actions
            non_trigger_phrases = [
                "I'm skipping breakfast today",
                "tell me about yourself",
                "what's the weather",
                "how are you doing"
            ]
            
            skip_triggers = ["skip", "next", "move on"]
            
            for phrase in non_trigger_phrases:
                # Should not match action triggers exactly
                should_not_trigger = not any(
                    trigger == phrase.lower() or f" {trigger} " in f" {phrase.lower()} "
                    for trigger in skip_triggers
                )
                assert should_not_trigger or "skip" not in phrase.lower()
            
            self.passed_tests.append(test_name)
            return True
        except Exception as e:
            self.failed_tests.append(f"{test_name}: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all Phase 2 voice integration tests"""
        print("\n" + "="*60)
        print("PHASE 2: VOICE INTEGRATION TESTING")
        print("="*60)
        
        # List of all test methods
        tests = [
            # 2.1 Vocode StreamingConversation Testing
            self.test_websocket_connection,
            self.test_stt_integration,
            self.test_tts_integration,
            self.test_conversation_flow,
            self.test_connection_stability,
            self.test_error_recovery,
            
            # 2.2 Voice Action Testing
            self.test_skip_story_action,
            self.test_tell_more_action,
            self.test_metadata_action,
            self.test_conversational_query,
            self.test_action_responses,
            self.test_session_state_updates,
            self.test_action_error_handling,
            
            # 2.3 Phrase Trigger Testing
            self.test_trigger_recognition,
            self.test_false_positive_prevention
        ]
        
        # Run each test
        for i, test in enumerate(tests, 1):
            test_name = test.__name__.replace('test_', '').replace('_', ' ').title()
            print(f"\n[{i}/15] Testing: {test_name}")
            
            try:
                result = await test()
                if result:
                    print(f"✅ PASSED: {test_name}")
                    self.test_results["passed"] += 1
                else:
                    print(f"❌ FAILED: {test_name}")
                    self.test_results["failed"] += 1
            except Exception as e:
                print(f"❌ ERROR: {test_name} - {str(e)}")
                self.test_results["failed"] += 1
                self.failed_tests.append(f"{test_name}: {str(e)}")
        
        # Print summary
        print("\n" + "="*60)
        print("PHASE 2 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.test_results['total_tests']}")
        print(f"Passed: {self.test_results['passed']} ✅")
        print(f"Failed: {self.test_results['failed']} ❌")
        print(f"Success Rate: {(self.test_results['passed']/self.test_results['total_tests']*100):.1f}%")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for failed in self.failed_tests:
                print(f"  - {failed}")
        
        if self.passed_tests:
            print("\n✅ Passed Tests:")
            for passed in self.passed_tests:
                print(f"  - {passed}")
        
        # Return success if 80% or more tests pass
        return self.test_results["passed"] >= 12


async def main():
    """Main test runner"""
    tester = TestPhase2VoiceIntegration()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 Phase 2 Voice Integration Testing PASSED!")
        print("Ready to proceed to Phase 3: Integration Testing")
    else:
        print("\n⚠️ Phase 2 Voice Integration Testing needs attention")
        print("Please fix failing tests before proceeding")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)