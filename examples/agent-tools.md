### AI Agent Tool Definitions

This document outlines the core tools available to the back-end AI agent. These tools are designed to handle user interruptions and provide dynamic responses during the daily newsletter briefing. Each tool is described with its purpose, how it's triggered, and the logic it will follow.

---

#### 1. Skip Story Tool

-   **Purpose:** To immediately stop the current story's audio and advance to the next story in the user's listening session.
-   **Trigger:** The user says "skip this story," "next," or a similar conversational phrase. The AI agent's intent recognition model will identify this command.
-   **Functionality:**
    -   The agent will halt the current audio playback.
    -   It will update the **`listening_sessions`** table in the database to increment the **`current_story_index`**.
    -   The agent will then begin providing the one-sentence summary for the new, next story.
-   **Implementation Note:** This is a straightforward, state-modifying tool that does not require an LLM for its primary function.

---

#### 2. Tell Me More Tool

-   **Purpose:** To provide a detailed, in-depth reading of the full text of the current story.
-   **Trigger:** The user says "tell me more," "go deeper," "what's the full story?" or a similar command.
-   **Functionality:**
    -   The agent will retrieve the full text of the current story from the **`stories`** table using the **`current_story_id`** from the active listening session.
    -   It will then use the Text-to-Speech (TTS) engine to read the entire **`full_text_summary`** field to the user.
    -   Once the reading is complete, the agent will return to a listening state, awaiting further user commands.
-   **Implementation Note:** This tool's primary action is data retrieval and playback, with no additional LLM processing required.

---

#### 3. Conversational Query Tool (Dynamic AI-Powered Responses)

-   **Purpose:** To handle complex user questions about a story that go beyond simple commands. This tool provides a conversational, context-aware answer using an LLM.
-   **Trigger:** The user asks a question about the current story's content, asks for external context, or makes a detailed inquiry. The intent recognition model will classify this as a question requiring a dynamic response.
-   **Functionality:**
    -   The back-end agent will formulate a prompt for a Large Language Model (LLM). This prompt will include:
        -   The **user's exact query** (e.g., "what's the significance of this event?").
        -   The **full text of the current story** for context.
        -   The **current date and any relevant real-world context** (e.g., "what has been going on in France in the past few months").
    -   The agent will pass this prompt to the LLM. For queries requiring up-to-date information, the agent should be configured to use a specialized LLM with web-Browse capabilities.
    -   The LLM will generate a relevant answer.
    -   The agent will use the TTS engine to read the LLM's answer to the user.
    -   After the response, the agent will resume the standard briefing from where it left off, either by continuing the current story or by moving to the next.
-   **Implementation Note:** This is the most complex tool, relying on advanced LLM prompting, potential tool-use (e.g., a web search tool), and a seamless integration between the LLM's output and the app's voice interface.

---

#### 4. Story Metadata Tool

-   **Purpose:** To provide information about the current story's metadata, such as its source newsletter, publication date, and headline. This helps users get quick facts without a detailed search.
-   **Trigger:** The user asks a direct question about the story's origin or publication details, such as "What newsletter is this from?", "When was this published?", or "Who wrote this story?".
-   **Functionality:**
    -   The agent will retrieve the metadata for the **`current_story_id`** from the **`stories`**, **`issues`**, and **`newsletters`** tables.
    -   It will construct a direct, factual response based on the retrieved data. For example, if the user asks for the newsletter source, the agent will return the `newsletters.name`.
    -   The agent will use the TTS engine to read this factual answer to the user.
    -   After the response, the agent will return to a listening state, ready for the next command.
-   **Implementation Note:** This tool is a simple data retrieval function that pulls specific fields from the database. It does not require a complex LLM query and is designed for a fast, direct response.