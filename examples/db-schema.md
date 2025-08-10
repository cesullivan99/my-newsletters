## DATABASE SCHEMA:

Here is a proposed database schema that would work well with your app's flow and the chosen tech stack, particularly a relational database like the one provided by Supabase.

### 1. `users` Table
This table stores user account information and preferences.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | **Primary key**. Unique identifier for the user. |
| `email` | `VARCHAR(255)` | User's email address (must be unique). |
| `name` | `VARCHAR(255)` | User's full name. |
| `created_at` | `TIMESTAMP` | Timestamp when the user account was created. |
| `default_voice_type` | `VARCHAR(50)` | Preferred AI voice for the user. |
| `default_playback_speed` | `FLOAT` | Default speed for audio playback. |
| `summarization_depth` | `VARCHAR(50)` | User's preference for story summary detail (e.g., "high-level", "detailed"). |

### 2. `newsletters` Table
This table stores information about the newsletters available for subscription.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | **Primary key**. Unique identifier for the newsletter. |
| `name` | `VARCHAR(255)` | Name of the newsletter. |
| `publisher` | `VARCHAR(255)` | Publisher of the newsletter. |
| `description` | `TEXT` | A brief description of the newsletter's content. |

### 3. `user_subscriptions` Table
This is a **junction table** to link users to the newsletters they are subscribed to.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `user_id` | `UUID` | **Foreign key** referencing `users.id`. |
| `newsletter_id` | `UUID` | **Foreign key** referencing `newsletters.id`. |
| `subscribed_at` | `TIMESTAMP` | Timestamp of when the user subscribed. |

### 4. `issues` Table
This table stores the daily or weekly issues of each newsletter.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | **Primary key**. Unique identifier for the issue. |
| `newsletter_id` | `UUID` | **Foreign key** referencing `newsletters.id`. |
| `date` | `DATE` | Date the issue was published. |
| `subject` | `VARCHAR(255)` | The subject line of the newsletter issue. |
| `raw_content` | `TEXT` | The full raw HTML or text content of the newsletter issue. |

### 5. `stories` Table
This table stores individual stories extracted from each issue.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | **Primary key**. Unique identifier for the story. |
| `issue_id` | `UUID` | **Foreign key** referencing `issues.id`. |
| `headline` | `TEXT` | The headline of the story. |
| `one_sentence_summary` | `TEXT` | The brief summary for the initial briefing. |
| `full_text_summary` | `TEXT` | A more detailed summary for "tell me more" requests. |
| `full_article` | `TEXT` | The text of the full article, scraped from its url (if possible)
| `url` | `TEXT` | URL to the original story, if available. |
| `audio_url` | `TEXT` | URL to the pre-generated audio for this story. |

### 6. `listening_sessions` Table
This table tracks each user's daily briefing session. This is critical for the AI agent to maintain state.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | **Primary key**. Unique identifier for the session. |
| `user_id` | `UUID` | **Foreign key** referencing `users.id`. |
| `created_at` | `TIMESTAMP` | Timestamp when the session was generated. |
| `current_story_id` | `UUID` | **Foreign key** referencing `stories.id`. The story the user is currently on. |
| `current_story_index` | `INT` | The index of the current story in the session's story list. |
| `session_status` | `VARCHAR(50)` | Current status of the session (e.g., 'playing', 'paused', 'completed'). |
| `story_order` | `TEXT[]` | An ordered array of `story_id`s for this session. |

### 7. `chat_logs` Table
This table stores the conversation history for each session, which is vital for the AI to handle interruptions and maintain context.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | **Primary key**. Unique identifier for the chat log entry. |
| `session_id` | `UUID` | **Foreign key** referencing `listening_sessions.id`. |
| `timestamp` | `TIMESTAMP` | Timestamp of the message. |
| `role` | `VARCHAR(50)` | The speaker of the message ('user' or 'assistant'). |
| `content` | `TEXT` | The transcript of the message. |
| `intent` | `VARCHAR(50)` | The AI's classification of the user's intent (e.g., 'tell_me_more', 'skip_story', 'get_source'). |