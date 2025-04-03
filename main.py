import streamlit as st
from google import genai
from google.genai import types
import tempfile
import os

# Set up the Gemini API client
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "file_uri" not in st.session_state:
    st.session_state.file_uri = None

# Streamlit UI title
st.title("Chat with Your PDF")

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
    st.success("PDF uploaded successfully!")

# Chat interface (only enabled if a PDF is uploaded)
if st.session_state.file_uri is not None:
    # Display chat history
    for message in st.session_state.messages:
        role = message.role
        with st.chat_message(role if role == "user" else "assistant"):
            parts = message.parts
            text_parts = [part.text for part in parts if hasattr(part, 'text')]
            file_parts = [part.file_uri for part in parts if hasattr(part, 'file_uri')]
            if file_parts and role == "user":
                st.markdown(f"[Document uploaded] {' '.join(text_parts)}")
            else:
                st.markdown(' '.join(text_parts))

    # Chat input
    user_input = st.chat_input("Ask me anything about the document...")

    if user_input:
        # Handle user input
        if not st.session_state.messages:
            # First query: include the PDF URI and user input
            st.session_state.messages.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(file_uri=st.session_state.file_uri, mime_type="application/pdf"),
                        types.Part.from_text(text=user_input),
                    ]
                )
            )
        else:
            # Subsequent queries: text only
            st.session_state.messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_input)]
                )
            )

        # Display user message immediately
        with st.chat_message("user"):
            if len(st.session_state.messages) == 1:
                st.markdown(f"[Document uploaded] {user_input}")
            else:
                st.markdown(user_input)

        # Generate and stream assistant response
        with st.chat_message("assistant"):
            with st.status("Assistant is thinking...", expanded=True) as status:
                contents = st.session_state.messages
                generate_content_config = types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="text/plain",
                )
                response_generator = client.models.generate_content_stream(
                    model="gemini-2.5-pro-exp-03-25",  # Replace with the correct model name if needed
                    contents=contents,
                    config=generate_content_config,
                )
                full_response = ""
                response_container = st.empty()
                for chunk in response_generator:
                    full_response += chunk.text
                    response_container.write(full_response)
                status.update(label="Response generated!", state="complete")

            # Append assistant response to history
            st.session_state.messages.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=full_response)]
                )
            )
else:
    st.info("Please upload a PDF to start chatting.")

