# **Meetbuddy**

This project simplifies **corporate meetings** by integrating transcription and summarization. Powered by **Worqhat APIs**, it transcribes audio/video files, summarizes content, extracts timelines, adds deadlines to **Google Calendar**, and stores data for easy retrieval.

---

## **Features**

- **Speech-to-Text**: Convert meeting audio or video files to text using **Worqhat's API**.
- **Text Summarization**: Generate concise summaries with extracted timelines.
- **Video Summarization**: Extract audio from video files, transcribe, and summarize.
- **Google Calendar Integration**: Automatically create calendar events for tasks.
- **Database Storage**: Store and retrieve meeting data using **MongoDB**.
- **Search and Export**: Search summaries by title or date range and export results.

---

## **Requirements**

- **Python**: 3.7 or later
- **Libraries**:
  - `streamlit`
  - `requests`
  - `pymongo`
  - `moviepy`
  - `google-auth-oauthlib`
  - `google-api-python-client`
- **MongoDB**: Hosted or local instance
- **Worqhat API Keys**: For speech-to-text and summarization
- **Google Calendar API**: For task scheduling

---

## **Setup Instructions**

### 1. Clone the Repository
```bash
git clone https://github.com/Ahad-23/RenAIssance-Hackathon.git
cd RenAIssance-Hackathon
```

### 2. Install Required Libraries
```bash
pip install -r requirements.txt
```
### 3. Set Up Environment Variables
Create a .env file in the project directory and set the following environment variables:
Example .env:
```bash
WORQHAT_TEXT_SUMMARIZER_API_KEY=your_worqhat_aicon-v4-nano-160824_api
WORQHAT_TEXT_SUMMARIZATION_API_KEY=your_worqhat_speech_to_text_api
MONGO_URI=your_mongo_uri
```


### 4. Set Up Google Calendar API
Go to the [Google Developer Console](https://console.cloud.google.com/).
Create a new project.
Enable the Google Calendar API.
Create OAuth 2.0 credentials and download the credentials.json file.
Rename it to client_secret.apps.googleusercontent.com.json and place it in the project directory.

### 5. Run the Application
```bash
streamlit run app.py
```

### 6. Access the Application
Open your browser and navigate to http://localhost:8501 to use the application.
