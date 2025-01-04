import streamlit as st
import google.generativeai as genai
from datetime import datetime
from PyPDF2 import PdfReader
import docx
import pyperclip
import time
import requests
from io import BytesIO
import base64
from gtts import gTTS
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')

# Configure API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

def read_file_content(uploaded_file):
    content = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
        elif uploaded_file.type == "text/plain":
            content = uploaded_file.getvalue().decode("utf-8")
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                content += para.text + "\n"
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
    return content

def chatbot(input_text, context=None):
    try:
        prompt = f"Context: {context}\n\nQuestion: {input_text}" if context else input_text
        response = model.generate_content(prompt)
        return {"text": response.text}
    except Exception as e:
        return {"text": f"Error: {str(e)}"}

def get_audio_html(text):
    try:
        tts = gTTS(text=text, lang='en')
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_base64 = base64.b64encode(audio_bytes.getvalue()).decode()
        return f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            </audio>
        """
    except Exception as e:
        st.error(f"Error generating audio: {str(e)}")
        return None

def process_audio_file(audio_file):
    """Process audio files using AssemblyAI API."""
    try:
        # AssemblyAI API Key - Replace with your key from https://www.assemblyai.com/ (free tier available)
        api_key = ASSEMBLYAI_API_KEY
        headers = {
            "authorization": api_key,
            "content-type": "application/json"
        }
        
        # Upload the audio file
        st.info("Uploading audio file...")
        upload_url = "https://api.assemblyai.com/v2/upload"
        
        # Read file data
        audio_data = audio_file.read()
        
        # Upload
        upload_response = requests.post(
            upload_url,
            headers=headers,
            data=audio_data
        )
        
        if upload_response.status_code == 200:
            audio_url = upload_response.json()["upload_url"]
            
            # Create transcription request
            transcript_url = "https://api.assemblyai.com/v2/transcript"
            json_data = {
                "audio_url": audio_url,
                "language_code": "en"
            }
            
            # Start transcription
            st.info("Starting transcription...")
            response = requests.post(
                transcript_url,
                json=json_data,
                headers=headers
            )
            
            if response.status_code == 200:
                transcript_id = response.json()["id"]
                
                # Poll for completion
                polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
                
                while True:
                    polling_response = requests.get(polling_endpoint, headers=headers)
                    polling_response = polling_response.json()
                    
                    if polling_response["status"] == "completed":
                        return polling_response["text"]
                    elif polling_response["status"] == "error":
                        st.error("Transcription failed")
                        return None
                        
                    # Wait before polling again
                    time.sleep(1)
            else:
                st.error("Failed to start transcription")
                return None
        else:
            st.error("Failed to upload audio file")
            return None
            
    except Exception as e:
        st.error(f"Error processing audio: {str(e)}")
        return None
    finally:
        # Reset file pointer
        audio_file.seek(0)

# Add this helper function
def make_chunks(audio_segment, chunk_length):
    """Split audio into smaller chunks for better processing."""
    chunks = []
    for i in range(0, len(audio_segment), chunk_length):
        chunks.append(audio_segment[i:i + chunk_length])
    return chunks

def main():
    st.title("AI Assistant")

    # Initialize session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Sidebar
    with st.sidebar:
        if st.button("+ New Chat"):
            st.session_state.conversation = []
            st.session_state.current_chat_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            if "file_content" in st.session_state:
                del st.session_state.file_content
            st.rerun()

        # Document upload
        st.subheader("Document Upload")
        uploaded_file = st.file_uploader(
            "Upload a document",
            type=["pdf", "docx", "txt"],
            key="doc_uploader"
        )
        if uploaded_file:
            st.session_state.file_content = read_file_content(uploaded_file)
            st.success("Document processed successfully!")

        # Audio upload section
        st.subheader("Audio Transcription")

        
        audio_file = st.file_uploader(
            "Upload audio file",
            type=["mp3", "wav", "m4a", "ogg"],
            key="audio_uploader"
        )
        
        if audio_file:
            # Show file details
            file_size = len(audio_file.getvalue()) / (1024 * 1024)  # Size in MB
            st.write(f"File size: {file_size:.1f} MB")
            
            # Show audio preview
            st.audio(audio_file)
            
            # Add transcribe button
            if st.button("🎤 Transcribe Audio", use_container_width=True):
                with st.spinner("Processing... This may take a minute."):
                    transcribed_text = process_audio_file(audio_file)
                    
                    if transcribed_text:
                        st.success("✨ Transcription complete!")
                        
                        # Show transcription with copy button
                        col1, col2 = st.columns([4,1])
                        with col1:
                            st.text_area(
                                "Transcribed Text:",
                                transcribed_text,
                                height=150
                            )
                        with col2:
                            if st.button("📋 Copy"):
                                pyperclip.copy(transcribed_text)
                                st.success("Copied!")
                        
                        # Add to chat
                        st.session_state.conversation.append({
                            "role": "user",
                            "content": f"🎤 Transcribed Audio:\n{transcribed_text}"
                        })
                        st.rerun()

    # Chat messages
    for message in st.session_state.conversation:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        with st.chat_message("user"):
            st.write(prompt)
        st.session_state.conversation.append({"role": "user", "content": prompt})

        # Get bot response
        with st.chat_message("assistant"):
            context = st.session_state.get("file_content", None)
            response = chatbot(prompt, context)
            
            st.write(response["text"])

            # Action buttons
            col1 = st.columns(3)
            if st.button("📋 Copy", key=f"copy_{len(st.session_state.conversation)}"):
                pyperclip.copy(response["text"])
                st.success("Copied!")
            
        st.session_state.conversation.append({"role": "assistant", "content": response["text"]})

if __name__ == "__main__":
    main()
