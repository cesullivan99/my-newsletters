### Audio Processing Job: Logical Flow

This document outlines the step-by-step process for the audio pre-processing job. The flow is designed to be run periodically, fetching new text content from the database and converting it into audio files for efficient streaming.

---

### 1. Job Initialization and Configuration

The job starts by setting up its environment. It initializes logging to track its progress and any potential errors. It then loads the necessary configuration details and API keys for external services, such as **Supabase** (for the database), a **Text-to-Speech (TTS) service**, and a **cloud storage client** (like Google Cloud Storage). These configurations are crucial for the job to connect to and interact with all required services.

---

### 2. Fetching New Stories

The first operational step is to query the database. The job fetches a list of stories that have been ingested but have not yet been converted to audio. This is typically done by looking for stories where the `summary_audio_url` or `full_text_audio_url` fields are empty or `NULL`.

---

### 3. Iterative Processing of Stories

The job then enters a loop, processing each story individually. For each story, it performs the following steps:

1.  **Text Extraction**: It retrieves the `one_sentence_summary` and `full_text_summary` from the story record.

2.  **Audio Conversion**: It sends the summary text to the TTS API to generate a brief audio clip. It then sends the full text to the TTS API to generate the full audio version.

3.  **Cloud Upload**: The generated audio files are uploaded to a designated cloud storage bucket. A logical folder structure, perhaps based on the story's ID, is used to keep the files organized.

4.  **URL Retrieval**: After a successful upload, the job retrieves the public or private URL for each new audio file.

---

### 4. Database Update

Once the audio files are uploaded and their URLs are generated, the job updates the corresponding story record in the database. It populates the `summary_audio_url` and `full_text_audio_url` fields with the new URLs. This ensures that the application can access the pre-processed audio files directly during a listening session without any further TTS API calls.

---

### 5. Error Handling and Completion

The entire process is wrapped in a robust error-handling mechanism to catch any failures during API calls, uploads, or database updates. If an error occurs, it is logged with details to assist with debugging. Finally, once all stories are processed, or if there were no new stories to begin with, the job logs a completion message and exits.