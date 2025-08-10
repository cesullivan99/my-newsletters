### FEATURE:

-   **Interactive AI Voice Assistant with Interruption Capability:** The core of MyNewsletters is an AI agent that delivers a daily audio briefing. A key feature is the user's ability to interrupt the AI at any point during the briefing.
-   **Dynamic Story Summarization:** The AI will initially provide a single, high-level, one-sentence summary for each story from the user's selected newsletters.
-   **Conversational Back-end Agent:** A sophisticated back-end AI agent will interpret natural language interruptions from the user. It will determine the user's intent from their conversational input (e.g., "tell me more," "what newsletter was this in," "skip") and trigger the appropriate tool or function to respond.
-   **Tool-Based Response System:** The back-end agent will be equipped with various "tools" or functions to handle user requests, such as a function to provide a more detailed story summary, a function to skip to the next story, or a function to retrieve the name of the newsletter for the current story.
-   **Gmail Newsletter Ingestion:** The app will authenticate with a user's Gmail account to automatically identify and pull newsletters from their inbox, which will then be parsed and stored in the database for processing.
-   **Audio Pre-Processing:** A pre-processing job will run after newsletter ingestion to convert all text content (summaries and full stories) into audio files. These files will be stored in a cloud bucket for efficient streaming during listening sessions. 🎧
-   **Sleek, Minimalistic, and Modern User Interface:** The app will feature a clean, intuitive, and aesthetically pleasing design that prioritizes ease of use and a fluid user experience.

***

### EXAMPLES:

-   `examples/db-schema.md` - A possible schema for the database - it is not strictly required that this precise schema is followed, but it could be helpful to use as a jumping-off point.
-   `examples/interrupt_handling_flow.md` - A conceptual markdown file that details the state machine for the AI agent, specifically how it transitions from the "briefing" state to an "interrupted" state, processes the user's request, and then returns to the "briefing" state.
-   `examples/agent-tools.md` - A markdown file showcasing the definitions for the tools the back-end agent will use. Examples would include the "skip story" tool, "tell me more" tool, and "conversational query" tool.
-   `examples/sample_conversations.json` - A document with multiple example conversation logs, demonstrating how the user might interrupt the AI, what the back-end agent's interpretation would be, and the resulting AI-generated response.
-   `examples/audio-processing-job.md` - A conceptual document outlining the flow for the pre-processing job, including calling the TTS API, uploading to a bucket, and updating the database with audio file URLs.

***

### DOCUMENTATION:

-   **Back-end Framework:** **Flask** - A lightweight and flexible Python web framework. [Flask Documentation](https://flask.palletsprojects.com/)
-   **AI Agent Framework:** **LangChain** - A popular and robust framework for building LLM-powered applications, with excellent support for agents and tool-calling. [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
-   **Front-end:** **React Native** - A JavaScript framework for building native mobile apps for both iOS and Android from a single codebase. [React Native Documentation](https://reactnative.dev/docs/getting-started)
-   **Database:** **Supabase** - An open-source Firebase alternative that provides a PostgreSQL database, authentication, and real-time capabilities. Its SQL database structure is a good fit for your detailed schema. [Supabase Documentation](https://supabase.com/docs). We can also use the [Supabase MCP server](https://github.com/supabase-community/supabase-mcp).
-   **Speech-to-Text (STT) & Text-to-Speech (TTS):** **Vocode** is an open-source Python library for creating real-time voice assistants that integrates with various STT/TTS providers and LLMs. [Vocode Documentation](https://docs.vocode.dev/). We will be using Vocode with ElevenLabs for TTS.
-   **Gmail API:** **Google's Gmail API** is essential for accessing user inboxes. The documentation will be vital for managing OAuth 2.0 authentication, searching for emails, and parsing message bodies. [Gmail API Documentation](https://developers.google.com/gmail/api/guides)

***

### OTHER CONSIDERATIONS:

-   **Latency:** The user's experience hinges on the responsiveness of the back-end agent. Pre-processing audio significantly reduces latency by eliminating on-the-fly TTS calls during a session.
-   **Intent Recognition:** The back-end AI's ability to accurately interpret the user's intent from a wide range of conversational phrases is crucial. It must handle variations like "go deeper," "expand on that," or "what's the deal with that?" all as a command to "tell me more."
-   **State Management:** The back-end agent must be stateful. It needs to know which story is currently being summarized to provide the correct context for a "tell me more" or "what newsletter" request.
-   **Gmail API Authentication:** Implementing the Gmail API requires a specific OAuth 2.0 flow. This is a critical development step that an AI assistant might struggle with. You'll need to set up an OAuth consent screen in the Google Cloud console and handle the token exchange process, which includes securely storing access and refresh tokens for each user.
-   **Newsletter Parsing:** The content of a newsletter can be in various formats (HTML, plain text). A robust method will be needed to parse the email body, identify the stories, and extract relevant text for summarization. This may require an AI tool to intelligently separate articles within a single email.
-   **Scalability:** Consider the potential for multiple users interacting with the agent simultaneously and how the back-end infrastructure will manage these concurrent sessions. The audio pre-processing and cloud storage approach enhances scalability by offloading a key resource-intensive task.
-   **UI/UX Design for Voice-First:** Achieving a sleek, minimalistic, and modern UI in a voice-first app like MyNewsletters will require careful attention to: ample whitespace, clear typography, intuitive navigation, subtle animations and feedback, and focus on essential elements.