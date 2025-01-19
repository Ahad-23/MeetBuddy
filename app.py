import os
import pickle
import re
from datetime import date
import streamlit as st
import requests
from io import BytesIO
import base64
from pymongo import MongoClient
from datetime import datetime
# import os
from moviepy import VideoFileClip
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# API Keys
worqhat_text_summarizer_api_key = os.getenv("WORQHAT_TEXT_SUMMARIZER_API_KEY")
worqhat_text_summarization_api_key = os.getenv("WORQHAT_TEXT_SUMMARIZATION_API_KEY")

# Google Calendar API setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
def authenticate_google_calendar():
    """
    Authenticate and create a Google Calendar API service.
    This function uses `credentials.json` to generate and store a token locally.
    """
    creds = None
    token_file = 'token.pickle'
    credentials_file = r"client_secret.apps.googleusercontent.com.json"

    try:
        # Check for an existing token file
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)

        # If there are no valid credentials, authenticate the user
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Ensure the credentials file exists
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file '{credentials_file}' not found. Please add it to your project directory."
                    )
                # Initialize the flow for authentication
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                # Run the local server for OAuth flow
                creds = flow.run_local_server(port=8080)

            # Save the new token for future use
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)

        # Return the authenticated service
        return build('calendar', 'v3', credentials=creds)

    except Exception as e:
        print(f"Error during Google Calendar authentication: {e}")
        raise
def create_calendar_event(service, title, event_datetime, duration=60):
    """
    Create a Google Calendar event.

    Args:
        service: Google Calendar API service instance.
        title: Title of the event.
        event_datetime: Datetime object representing the event's start time.
        duration: Duration of the event in minutes (default: 60).

    Returns:
        str: Link to the created event.
    """
    # end_datetime=event_datetime+duration
    event = {
        'summary': title,  # Ensure the title is correctly passed here
        'start': {
            'dateTime': event_datetime.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': event_datetime.isoformat(),
            'timeZone': 'UTC',
        },
    }


    try:
        # Insert the event into Google Calendar
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return created_event.get('htmlLink')
    except Exception as e:
        raise RuntimeError(f"Error creating event: {e}")



# Set page configuration
st.set_page_config(
    page_title="Corporate Use Case: Online Meeting Summarizer",
    layout="wide",
    initial_sidebar_state="expanded",
)

#Set the db connection
client = MongoClient(os.getenv("MONGO_URI")) 
db = client["Summary_history"] 
collection = db["details"]

#Extracts Timelines
def timeline(summary):
    """
    Extract only the date and title (task) from the timeline summary.
    The API will be called with the provided summary to retrieve date and title.
    """
    timeline = call_timeline_api(summary, worqhat_text_summarizer_api_key)
    timeline_list = timeline.splitlines()  # Split the timeline into individual lines (date + task)
    return timeline_list

#Form to insert data to db
def insert_db(meeting_title,transcribe,summary,timeline):
    if meeting_title.strip():

        # Process attendees (split by newline)
        attendee_list = attendees.splitlines()
        summary_document = {
        "meeting_date": meeting_date_str,
        "meeting_day": meeting_day,
        "meeting_title":meeting_title,
        "transcribed_text":transcribe,
        "summary_text": summary,
        "attendees": attendee_list, 
        "Timelines": timeline 
        }
        result = collection.insert_one(summary_document)
        print(f"Summary inserted with ID: {result.inserted_id}")
    else:
        st.error("Name is required!")

# Helper Functions
def video_to_audio(video_path):
    video = VideoFileClip(video_path)
    audio_file = "audio.wav"
    video.audio.write_audiofile(audio_file)
    return audio_file

#For calling APIs
def call_api(url, headers, data=None, files=None):
    response = requests.post(url, headers=headers, json=data, files=files)
    response.raise_for_status()
    return response.json()

def call_speech_to_text_api(audio_file, api_key):
    url = "https://api.worqhat.com/api/ai/speech-text"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"audio": audio_file.getvalue()}
    return call_api(url, headers, files=files)["data"]["text"]

def call_text_summarization_api(text, api_key,meet_day,meet_date):
    url = "https://api.worqhat.com/api/ai/content/v4"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "question": "Day:"+meet_day+"Date:"+str(meet_date)+text,
        "model": "aicon-v4-nano-160824",
        "randomness": 0.5,
        "stream_data": False,
        "training_data": (
            """summarise the transcripts of a meeting under 100-120 words pointwise, increase the wordcount only if necessary,
            the wordcount should only increase if all necessary points couldn't be included and also add discussed timelines date wise
            mapping it to the task or work assigned for that particular date pls give exact dates as per the discussion mapping the
            key words like tomorrow, day after tomorrow,etc to the current date and give it in the format dd-mm-yyyy
            Dont ask annything else at all and dont add day in the reply"""
        ),
        "response_type": "text"
    }
    return call_api(url, headers, data=data)["content"]

def call_timeline_api(text, api_key):
    """
    Call the Worqhat API to extract the timeline from the given text.
    This API returns the timeline section in the form of date and task in one line.
    """
    url = "https://api.worqhat.com/api/ai/content/v4"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "question": text,
        "model": "aicon-v4-nano-160824",
        "randomness": 0.5,
        "stream_data": False,
        "training_data": (
            """Extract only the timeline section from the provided input. Remove the word 'timeline' as a topic heading,
            and please don't put any other text apart from that. Return it in the form of date and task with one date task pair in each line.
            the output should be date (in dd-mm-yyyy):the task assigned"""

        ),
        "response_type": "text"
    }
    return call_api(url, headers, data=data)["content"]

def handle_transcription_and_summary(audio_file, api_key,meeting_day,meeting_date_str):
    transcription = call_speech_to_text_api(audio_file, api_key)
    st.session_state.transcription = transcription
    st.session_state.summarize_active = True
    st.subheader("Transcription Result")
    st.write(transcription)
    
    if st.session_state.summarize_active:
        summary = call_text_summarization_api(transcription, worqhat_text_summarizer_api_key,meeting_day,meeting_date_str)
        st.subheader("Transcription Summary")
        summary_start_index=summary.find("Summary:")
        st.write(summary[summary_start_index+len("Summary:\n\n"):])
        return summary,transcription

# UI Design
st.title("Corporate Use Case: Online Meeting Summarizer")
st.write("Streamline your meetings with powerful transcription, summarization, and video recording tools.")



tab1, tab2, tab3, tab4 = st.tabs(["📝 Speech-to-Text", "📄 Text Summarization", "📹 Video Summarizer", "🔍 Summary Viewer"])

# Speech-to-Text Tab
with tab1:
    st.header("Speech-to-Text from Worqhat")
    st.write("Upload an audio or video file to transcribe.")
    col3,col4=st.columns(2)
    with col3:
        with st.form("my_form_tab1"):
            meeting_title = st.text_input("Meeting Title")
            meeting_date = st.date_input("Meeting Date", value=date.today())
            meeting_date_str = meeting_date.strftime("%Y-%m-%d")
            meeting_day=meeting_date.strftime("%A")
            attendees = st.text_area("Enter attendee names (one per line)",placeholder="Optional")
            audio_file = st.file_uploader("Upload your file", type=["mp3", "wav", "mp4"])
            Summarize = st.form_submit_button("Summarize")
    with col4:
        # st.subheader("Summary Result")
        if Summarize:
            if audio_file:
                summary,transcription = handle_transcription_and_summary(audio_file, worqhat_text_summarization_api_key,meeting_day,meeting_date_str)
                summary_start_index=summary.find("Summary:")
                summary_print=summary[summary_start_index+len("Summary:\n\n"):] 
                timeline_list=timeline(summary)
                for i in timeline_list:
                    # Authenticate and create a calendar event
                    service = authenticate_google_calendar()
                    colon_index=i.find(":")
                    if colon_index == -1:
                            # Handle case where no colon is found
                            print(f"Warning: Timeline entry '{i}' doesn't contain a deadline. Skipping event creation.")
                            continue

                    title = i[colon_index:]
                    try:
                        deadline_str = i[:colon_index].strip()  # Remove leading/trailing whitespace
                        deadline = datetime.strptime(deadline_str, "%d-%m-%Y")
                        cal_link=event_link = create_calendar_event(service, title, deadline)
                        st.success(f"Event created successfully: [View Event]({cal_link})")
                    except ValueError:
                        print(f"Warning: Invalid deadline format in '{i}'. Skipping event creation.")
                    # title=i[colon_index:]
                    # deadline=i[:colon_index]
                    # deadline=datetime.strptime(deadline, "%d-%m-%Y")
                    # cal_link=event_link = create_calendar_event(service, title, deadline)
                timeline_start = summary.find("**Timelines:**\n\n")
                
                # st.success(f"Event created successfully: [View Event]({cal_link})")
                insert_db(meeting_title,transcription,summary[summary_start_index+len("Summary:\n\n"):timeline_start],timeline_list)
            else:
                st.error("Please enter audio to summarize.")


# Text Summarization Tab
with tab2:
    st.header("Text Summarization from Worqhat")
    st.write("Paste text to summarize.")
    col1,col2=st.columns(2)
    with col1:
        with st.form("my_form_tab2"):
            meeting_title = st.text_input("Meeting Title")
            meeting_date = st.date_input("Meeting Date", value=date.today())
            meeting_date_str = meeting_date.strftime("%Y-%m-%d")
            meeting_day=meeting_date.strftime("%A")
            attendees = st.text_area("Enter attendee names (one per line)",placeholder="Optional")
            input_text = st.text_area("Input Text")
            Summarize = st.form_submit_button("Summarize")
    with col2:
        st.subheader("Summary Result")
        if Summarize:
            if input_text.strip():
                summary = call_text_summarization_api(input_text, worqhat_text_summarizer_api_key,meeting_day,meeting_date_str)
                summary_start_index=summary.find("Summary:")
                timeline_list=timeline(summary)
                summary_print=summary[summary_start_index+len("Summary"):]
                st.write(summary_print)
                for i in timeline_list:
                    # Authenticate and create a calendar event
                    service = authenticate_google_calendar()
                    colon_index=i.find(":")
                    if colon_index == -1:
                            # Handle case where no colon is found
                            print(f"Warning: Timeline entry '{i}' doesn't contain a deadline. Skipping event creation.")
                            continue

                    title = i[colon_index:]
                    try:
                        st.write(i)
                        deadline_str = i[:colon_index].strip()  # Remove leading/trailing whitespace
                        deadline = datetime.strptime(deadline_str, "%d-%m-%Y")
                        cal_link=event_link = create_calendar_event(service, title, deadline)
                        st.success(f"Event created successfully: [View Event]({cal_link})")
                    except ValueError:
                        print(f"Warning: Invalid deadline format in '{i}'. Skipping event creation.")
                    title=i[colon_index:]
                timeline_start = summary.find("**Timelines:**\n\n")
                insert_db(meeting_title,input_text,summary[summary_start_index+len("Summary:\n\n"):timeline_start],timeline_list)
            else:
                st.error("Please enter text to summarize.")
            

# Video Recording Tab
with tab3:
    st.header("Video Recording for Presentations")
    st.write("Record and download a presentation video.")
    col5,col6=st.columns(2)
    with col5:
        with st.form("my_form_tab3"):
            meeting_title = st.text_input("Meeting Title")
            meeting_date = st.date_input("Meeting Date", value=date.today())
            meeting_date_str = meeting_date.strftime("%Y-%m-%d")
            meeting_day=meeting_date.strftime("%A")
            attendees = st.text_area("Enter attendee names (one per line)",placeholder="Optional")
            uploaded_video = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi", "mkv"])
            Summarize = st.form_submit_button("Summarize")
    with col6:
        # st.subheader("Summary Result")
        if Summarize:
            if uploaded_video:
                video_path = os.path.join("temp_video.mp4")
                with open(video_path, "wb") as f:
                    f.write(uploaded_video.read())
                audio_path = video_to_audio(video_path)
                with open(audio_path, "rb") as audio_file:
                    
                    summary,transcription = handle_transcription_and_summary(BytesIO(audio_file.read()), worqhat_text_summarization_api_key,meeting_day,meeting_date_str)
                    timeline_list=timeline(summary)
                    summary_start_index=summary.find("Summary:")
                    summary_print=summary[summary_start_index+len("Summary:\n\n"):]
                    # st.write(summary_print)
                    for i in timeline_list:
                    # Authenticate and create a calendar event
                        service = authenticate_google_calendar()
                        colon_index=i.find(":")
                        if colon_index == -1:
                            # Handle case where no colon is found
                            print(f"Warning: Timeline entry '{i}' doesn't contain a deadline. Skipping event creation.")
                            continue

                        title = i[colon_index:]
                        try:
                            deadline_str = i[:colon_index].strip()  # Remove leading/trailing whitespace
                            deadline = datetime.strptime(deadline_str, "%d-%m-%Y")
                            cal_link=event_link = create_calendar_event(service, title, deadline)
                            st.success(f"Event created successfully: [View Event]({cal_link})")
                        except ValueError:
                            print(f"Warning: Invalid deadline format in '{i}'. Skipping event creation.")
                        title=i[colon_index:]
                        
                        
                    # summary_start_index=summary.find("Summary:")
                    timeline_start = summary.find("**Timelines:**\n\n")
                    # summary_print=summary[summary_start_index+len("Summary:\n\n"):]
                    # st.write(summary_print)
                    
                    insert_db(meeting_title,transcription,summary[summary_start_index+len("Summary:\n\n"):timeline_start],timeline_list)
            else:
                st.error("Please enter text to summarize.")

# Summary Viewer Tab
with tab4:
    st.header("Summary Viewer")
    st.write("Review and export meeting summaries.")
    # Inputs for searching
    st.subheader('Search Criteria')
    search_method = st.radio(
    "How do you want to search?",
    ("By Date Range", "By Meeting Title"))

# Inputs based on user's choice
    if search_method == "By Date Range":
        start_date = st.date_input('Start Date')
        end_date = st.date_input('End Date')
        title = None  # No need to input title for date range search
    elif search_method == "By Meeting Title":
        start_date = None  # No need for date inputs
        end_date = None
        title = st.text_input('Meeting Title')

    # Convert date input to string format for MongoDB query
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None

    # Button to trigger the search
    if st.button('Search Meetings'):
        query = {}

        # Search by Date Range
        if search_method == "By Date Range":
            if start_date_str and end_date_str:
                query["meeting_date"] = {
                    "$gte": start_date_str,
                    "$lte": end_date_str
                }
            elif start_date_str:
                query["meeting_date"] = {"$gte": start_date_str}
            elif end_date_str:
                query["meeting_date"] = {"$lte": end_date_str}
        
        # Search by Meeting Title
        elif search_method == "By Meeting Title" and title:
            query["meeting_title"] = {"$regex": title, "$options": "i"}  # Case-insensitive search

        # Query the database
        results = collection.find(query)
        meetings = list(results)

        if meetings:
            st.subheader('Search Results')
            
            # Using columns to display results more organized
            for meeting in meetings:
                with st.expander(f"{meeting.get('meeting_title')} - {meeting.get('meeting_date')}"):
                    col1, col2 = st.columns([2, 3])
                    
                    with col1:
                        st.markdown("### *Date*:")
                        st.write(meeting.get('meeting_date'))
                        
                        st.markdown("### *Day*:")
                        st.write(meeting.get('meeting_day'))

                    with col2:
                        st.markdown("### *Summary*:")
                        st.write(meeting.get('summary_text'))

                        st.markdown("### *Transcribed Text*:")
                        st.write(meeting.get('transcribed_text'))

                    st.markdown("### *Attendees*:")
                    attendees = meeting.get('attendees', [])
                    if attendees:
                        st.write(", ".join(attendees))
                    else:
                        st.write("No attendees listed.")
                    
                    st.write("---")
        else:
            st.write("No meetings found for the given search criteria.")

st.markdown("---")
st.markdown("Developed for corporate use by integrating Worqhat's speech-to-text and summarization APIs.")
