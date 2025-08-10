### Interruption Handling Flow

This document details the state machine and flow for how the AI agent will handle user interruptions during a listening session. The process is designed to be seamless and responsive, allowing the user to take control of the session at any time.

---

### 1. Session States

The AI agent operates within two primary states during a listening session:

-   **Briefing State:** The agent is actively reading a one-sentence summary of a newsletter story.
-   **Listening State:** The agent is paused, awaiting a user command after completing a summary or being interrupted.

---

### 2. The Interruption Loop

The following flow describes how the system transitions between these states and processes user commands.

1.  **Start of a New Story:**
    -   The agent begins in the **Briefing State**, reading a one-sentence summary for the current story.
    -   While reading, the system's Speech-to-Text (STT) component is always active, listening for user input.

2.  **User Interruption:**
    -   The user speaks a command (e.g., "skip," "tell me more," or a question).
    -   The STT component detects the voice and immediately sends the transcript to the back-end agent.
    -   The agent **pauses the audio playback** of the current summary. This is a critical step for a seamless user experience. The system is now in the **Listening State**.

3.  **Intent Recognition and Tool Calling:**
    -   The back-end agent receives the user's transcribed query.
    -   It uses a pre-trained LLM for **intent recognition**. The LLM analyzes the query to determine the user's goal.
    -   The recognized intent maps to one of the available tools:
        -   `Skip Story Tool`: Triggered by commands like "skip," "next," or "move on."
        -   `Tell Me More Tool`: Triggered by phrases like "tell me more," "go deeper," or "what's the full story?"
        -   `Conversational Query Tool`: Triggered by any question that requires a contextual or external response (e.g., "Who wrote this?," "What happened in France?").

4.  **Executing the Tool:**
    -   The agent calls the appropriate tool function, passing any necessary arguments (like the `current_story_id`).
    -   **Example: User says "skip."**
        -   The agent calls the `skip_story` tool.
        -   The tool updates the database to advance the session to the next story.
        -   The agent then uses the Text-to-Speech (TTS) component to provide a brief confirmation, like "Skipping this story," before starting the next one.

    -   **Example: User says "what's the full story?"**
        -   The agent calls the `tell_me_more` tool.
        -   The tool retrieves the full text and passes it to the TTS engine.
        -   The agent reads the detailed summary to the user.

    -   **Example: User asks "what's the capital of that country?"**
        -   The agent calls the `conversational_query` tool.
        -   It constructs a detailed prompt for an LLM that includes the user's question and the full story text for context.
        -   The LLM generates a response, which the agent then reads back to the user via TTS.

5.  **Resuming the Session:**
    -   After the tool's action is completed and the agent has provided a verbal response, the system returns to its default operation.
    -   If the user asked a question, the agent may ask if they want to continue with the current story before resuming the briefing. For commands like "skip," the agent simply starts the next story.
    -   The session returns to the **Briefing State**, either continuing the current story's summary or moving on to the next one.

This loop ensures that the user maintains complete control over their daily briefing, making the experience truly interactive and conversational.