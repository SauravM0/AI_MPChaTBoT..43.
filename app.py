import os
import ssl
import streamlit as st
import google.generativeai as genai
import json
from datetime import datetime
from PyPDF2 import PdfReader
import docx
import pandas as pd
import io

# Configure SSL and API
ssl._create_default_https_context = ssl._create_unverified_context
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key='GEMINI_API_KEY')

# Utility Functions
def chatbot(input_text, context=None):
    """Generate a response from the chatbot model with optional context."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        if context:
            prompt = f"""Context: {context}\n\nQuestion: {input_text}\n
            Please answer the question based on the provided context. If the question cannot be answered from the context, please say so."""
        else:
            prompt = input_text
            
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"An error occurred while generating response: {str(e)}")
        return "Sorry, I couldn't process that. Please try again."

def generate_chat_title(conversation):
    """Generate a title based on the first user message."""
    if conversation:
        first_message = conversation[0]["user"]
        title = first_message.split('.')[0][:30]
        return f"{title}..."
    return f"New Chat {datetime.now().strftime('%Y-%m-%d')}"

def load_chat_history():
    """Load all available chat histories."""
    try:
        with open('chat_histories.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        st.error("Error reading chat history file. Creating new history.")
        return {}

def save_chat_history(chat_id, conversation, title=None):
    """Save chat history to JSON file."""
    try:
        histories = load_chat_history()
        histories[chat_id] = {
            'title': title or generate_chat_title(conversation),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'conversation': conversation
        }
        with open('chat_histories.json', 'w') as f:
            json.dump(histories, f, indent=4)
    except Exception as e:
        st.error(f"Error saving chat history: {str(e)}")

def display_conversation():
    """Display the conversation in the chat container."""
    for exchange in st.session_state.conversation:
        with st.container():
            # User message
            st.markdown(
                f"""
                <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin: 5px 0;">
                    <strong>You:</strong> {exchange['user'].replace('</div>', '').strip()}
                </div>
                """, 
                unsafe_allow_html=True
            )
            # Bot message
            st.markdown(
                f"""
                <div style="background-color: #e1f5fe; padding: 10px; border-radius: 5px; margin: 5px 0;">
                    <strong>Chatbot:</strong> {exchange['bot'].replace('</div>', '').strip()}
                </div>
                """, 
                unsafe_allow_html=True
            )

def apply_custom_styles():
    """Apply custom styles to the application."""
    st.markdown("""
        <style>
        /* Main styles */
        .stApp {
            background-color: white;
            color: black !important;
        }
        
        /* Sidebar styles */
        [data-testid="stSidebar"] {
            background-color: white;
            color: black !important;
        }
        
        .stButton button {
            background-color: white;
            color: black !important;
            border: 1px solid #e0e0e0;
            transition: all 0.3s ease;
        }
        
        .stButton button:hover {
            background-color: #f0f0f0 !important;
            border-color: #d0d0d0;
        }
        
        /* Chat styles */
        .stMarkdown, .stContainer {
            background-color: white;
            color: black !important;
        }
        
        .stTextInput input {
            background-color: white;
            color: black !important;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            padding: 8px;
        }
        
        /* Header and decoration */
        [data-testid="stDecoration"] {
            display: none;
        }
        
        .stApp header {
            background-color: white;
            color: black !important;
        }
        
        /* Text elements */
        p, span, label, div, h1, h2, h3, h4, h5, h6 {
            color: black !important;
        }
        
        /* Toolbar and menu */
        .stToolbar {
            background-color: white !important;
        }
        
        button[kind="menuButton"] {
            background-color: white !important;
            color: black !important;
        }
        
        .stToolbar button svg {
            fill: black !important;
        }
        
        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [data-baseweb="menu"] li {
            background-color: white !important;
            color: black !important;
        }
        
        [data-baseweb="menu"] li:hover {
            background-color: #f0f0f0 !important;
        }
        
        /* Links */
        a {
            color: #0066cc !important;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }

        /* Sidebar section styling */
        .sidebar-section {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        .sidebar-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #1a1a1a !important;
            padding-bottom: 8px;
            border-bottom: 2px solid #e0e0e0;
        }

        .file-upload-section {
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 10px;
            background-color: #f0f7ff;
            border: 1px solid #cce5ff;
        }

        .chat-history-section {
            margin-bottom: 20px;
        }

        .chat-button {
            margin-bottom: 8px;
            transition: all 0.3s ease;
        }

        .chat-button:hover {
            transform: translateX(5px);
        }

        .divider {
            margin: 20px 0;
            border-top: 1px solid #e0e0e0;
        }

        .file-info {
            font-size: 14px;
            color: #666;
            margin-top: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

def new_chat():
    """Start a new chat session."""
    st.session_state.current_chat_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    st.session_state.conversation = []
    st.session_state.counter = 0

def read_file_content(uploaded_file):
    """Extract text content from various file types."""
    content = ""
    file_type = uploaded_file.type
    
    try:
        if file_type == "application/pdf":
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
                
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                content += para.text + "\n"
                
        elif file_type == "text/plain":
            content = uploaded_file.getvalue().decode("utf-8")
            
        elif file_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            df = pd.read_excel(uploaded_file)
            content = df.to_string()
            
        elif file_type == "text/csv":
            df = pd.read_csv(uploaded_file)
            content = df.to_string()
            
        return content
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None

def main():
    """Main application function."""
    # Initialize session state
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "counter" not in st.session_state:
        st.session_state.counter = 0

    # Apply custom styles
    apply_custom_styles()
    
    st.title("AI Chatbot")

    # Sidebar
    with st.sidebar:
        # File Upload Section
        st.markdown('<p class="sidebar-title">📁 File Upload</p>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Upload a file to chat",
            type=["pdf", "docx", "txt", "csv", "xlsx"],
            help="Supported formats: PDF, Word, TXT, CSV, Excel"
        )
        
        if uploaded_file:
            file_content = read_file_content(uploaded_file)
            if file_content:
                st.session_state.file_content = file_content
                st.markdown(
                    f'<div class="file-info">✅ File: {uploaded_file.name}</div>',
                    unsafe_allow_html=True
                )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Chat History Section
        st.markdown('<div class="chat-history-section">', unsafe_allow_html=True)
        st.markdown('<p class="sidebar-title">💬 Chat History</p>', unsafe_allow_html=True)
        
        # New Chat Button
        if st.button("🔵 Start New Chat", 
                    use_container_width=True,
                    type="primary"):
            new_chat()
            if "file_content" in st.session_state:
                del st.session_state.file_content
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # Display chat history
        histories = load_chat_history()
        sorted_histories = dict(sorted(
            histories.items(),
            key=lambda x: x[1]['timestamp'],
            reverse=True
        ))
        
        for chat_id, chat_data in sorted_histories.items():
            date = datetime.strptime(chat_data['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%b %d')
            button_label = f"💭 {chat_data['title']}\n📅 {date}"
            
            st.markdown('<div class="chat-button">', unsafe_allow_html=True)
            if st.button(button_label, key=chat_id, use_container_width=True):
                st.session_state.current_chat_id = chat_id
                st.session_state.conversation = chat_data['conversation']
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Main chat interface
    chat_container = st.container()
    with chat_container:
        display_conversation()

    # Input area
    with st.container():
        col1, col2 = st.columns([6,1])
        
        with col1:
            user_input = st.text_input(
                "",
                placeholder="Type your message here...",
                key=f"user_input_{st.session_state.counter}",
                label_visibility="collapsed"
            )
        
        with col2:
            send_button = st.button("Send")

        if user_input and (send_button or True):
            # Use file content as context if available
            context = st.session_state.get("file_content", None)
            response = chatbot(user_input, context)
            
            st.session_state.conversation.append({
                "user": user_input,
                "bot": response
            })
            save_chat_history(
                st.session_state.current_chat_id,
                st.session_state.conversation
            )
            st.session_state.counter += 1
            st.rerun()

if __name__ == '__main__':
    main()
