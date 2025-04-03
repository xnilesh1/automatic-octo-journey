import streamlit as st
from google import genai
from google.genai import types
import tempfile
import os

# Set up the Gemini API client
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []  # For display purposes
if "api_messages" not in st.session_state:
    st.session_state.api_messages = []  # For API calls
if "file_uri" not in st.session_state:
    st.session_state.file_uri = None

# Streamlit UI title
st.title("Chat with Your PDF")



def load_custom_css(file_path):
    with open(file_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_custom_css("custom.css")

# File uploader for PDF
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

# Handle PDF upload
if uploaded_file is not None and st.session_state.file_uri is None:
    # Save the uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name
    
    # Upload to Gemini API and get file URI
    file = client.files.upload(file=tmp_path)
    st.session_state.file_uri = file.uri
    
    # Clean up temporary file
    os.remove(tmp_path)
    
    # Reset conversation when a new PDF is uploaded
    st.session_state.messages = []
    st.session_state.api_messages = []
    
    st.success("PDF uploaded successfully!")

# Chat interface (only enabled if a PDF is uploaded)
if st.session_state.file_uri is not None:
    # Display chat history (for UI only)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    user_input = st.chat_input("Ask me anything about the document...")

    if user_input:
        # Add user message to display history
        if len(st.session_state.messages) == 0:
            # First message indication
            user_message = f"[Document uploaded] {user_input}"
        else:
            user_message = user_input
            
        # Update UI message history
        st.session_state.messages.append({"role": "user", "content": user_message})
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(user_message)
        
        # Create or update API message structure
        if len(st.session_state.api_messages) == 0:
            # First query: Include PDF reference
            initial_message = types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(file_uri=st.session_state.file_uri, mime_type="application/pdf"),
                    types.Part.from_text(text=user_input)
                ]
            )
            st.session_state.api_messages = [initial_message]
        else:
            # Subsequent queries: Add to the conversation
            new_message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_input)]
            )
            st.session_state.api_messages.append(new_message)

        # Generate and stream assistant response
        with st.chat_message("assistant"):
            with st.status("Assistant is thinking...", expanded=True) as status:
                try:
                    generate_content_config = types.GenerateContentConfig(
                        temperature=0.3,
                        response_mime_type="text/plain",
                    )
                    
                    response_generator = client.models.generate_content_stream(
                        model="gemini-2.5-pro-exp-03-25",
                        contents=st.session_state.api_messages,
                        config=generate_content_config,
                    )
                    
                    full_response = ""
                    response_container = st.empty()
                    for chunk in response_generator:
                        if hasattr(chunk, 'text'):
                            full_response += chunk.text
                            response_container.write(full_response)
                    
                    status.update(label="Response generated!", state="complete")
                    
                    # Add assistant response to both histories
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                    # Add to API history
                    assistant_message = types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=full_response)]
                    )
                    st.session_state.api_messages.append(assistant_message)
                    
                except Exception as e:
                    error_message = f"Error generating response: {str(e)}"
                    st.error(error_message)
                    status.update(label="Error occurred!", state="error")
else:
    st.info("Please upload a PDF to start chatting.")

# Add a button to clear conversation if needed
if st.session_state.file_uri is not None and len(st.session_state.messages) > 0:
    if st.button("Clear conversation"):
        st.session_state.messages = []
        # Keep the file reference but start a new conversation
        initial_system_message = types.Content(
            role="user",
            parts=[types.Part.from_uri(file_uri=st.session_state.file_uri, mime_type="application/pdf")]
        )
        st.session_state.api_messages = [initial_system_message]
        st.rerun()
        
        
