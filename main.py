import streamlit as st
import os
import tempfile
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Page configuration
st.set_page_config(page_title="PDF Chat with Gemini", page_icon="📄", layout="wide")

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

if "file_uri" not in st.session_state:
    st.session_state.file_uri = None

# App title and description
st.title("💬 Chat with your PDF")
st.markdown("Upload a PDF document and ask questions about its content")

# Sidebar for API key input
api_key = os.getenv("GOOGLE_API_KEY")

# Function to process PDF and initialize Gemini client
def process_pdf(uploaded_file):
    if api_key:
        try:
            # Initialize Gemini client
            client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
            
            # Create a temporary file to save the uploaded file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # Upload the file to Gemini
            file = client.files.upload(file=tmp_file_path)
            
            # Clean up the temporary file
            os.unlink(tmp_file_path)
            
            return client, file
        
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            return None, None
    else:
        st.error("Please enter your Gemini API Key in the sidebar.")
        return None, None

# Function to generate response from Gemini
def get_completion(messages, file_uri):
    if not api_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
        return
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = "gemini-2.5-pro-exp-03-25"  # Using the same model as in your example
    
    # Construct the initial prompt with the PDF file
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_uri(
                    file_uri=file_uri,
                    mime_type="application/pdf",
                ),
                types.Part.from_text(text=messages[-1]["content"]),
            ],
        ),
    ]
    
    # Configure generation parameters
    generate_content_config = types.GenerateContentConfig(
        temperature=0.3,
        response_mime_type="text/plain",
    )
    
    thinking_complete = False
    response = ""
    thinking = ""
    final_answer = ""
    
    # Stream the response and separate thinking from final answer
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        text_chunk = chunk.text if hasattr(chunk, 'text') else ""
        
        # Check if we've moved from thinking to final answer
        if not thinking_complete and "Okay, here" in text_chunk or "Here's the" in text_chunk:
            thinking_complete = True
        
        # Add text to appropriate section
        if not thinking_complete:
            thinking += text_chunk
        else:
            final_answer += text_chunk
        
        # Yield the combined text (this will be used for display in the UI)
        response = thinking + final_answer
        yield response

# Main layout - PDF upload area
uploaded_file = st.file_uploader("Upload a PDF document", type="pdf", key="pdf_uploader")

# Process the PDF when uploaded
if uploaded_file and (st.session_state.uploaded_file != uploaded_file.name):
    st.session_state.uploaded_file = uploaded_file.name
    
    with st.status("Processing PDF...", expanded=True) as status:
        st.write("Uploading file to Gemini API...")
        client, file = process_pdf(uploaded_file)
        
        if file:
            st.session_state.file_uri = file.uri
            status.update(label="PDF processed successfully!", state="complete", expanded=False)
            
            # Clear previous messages when a new PDF is uploaded
            st.session_state.messages = []
            
            # Add system message
            st.session_state.messages.append({
                "role": "assistant", 
                "content": f"I've processed your PDF '{uploaded_file.name}'. Ask me any questions about it!"
            })
            st.rerun()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if st.session_state.file_uri:
    user_input = st.chat_input("Ask a question about your PDF...")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Stream assistant response with thinking process displayed
        with st.chat_message("assistant"):
            with st.status("Thinking...", expanded=True) as status:
                response_generator = get_completion(st.session_state.messages, st.session_state.file_uri)
                full_response = ""
                
                # Stream the thinking and response
                for response_chunk in response_generator:
                    full_response = response_chunk
                    status.update(label="Gemini's thinking process:", state="running")
                    status.write(full_response)
                
                # When complete, update status
                status.update(label="Thought process complete", state="complete", expanded=False)
                
                # Display final answer
                st.markdown(full_response)
        
        # Add assistant response to message history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
else:
    st.info("Please upload a PDF document to start chatting.")
