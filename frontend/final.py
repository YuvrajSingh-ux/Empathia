import streamlit as st
from io import BytesIO
import requests
import pyttsx3
import tempfile
import os
import base64
import os
from dotenv import load_dotenv
from streamlit_mic_recorder import mic_recorder
import uuid
from streamlit.components.v1 import html

load_dotenv()

# import threading,time


# API_ENDPOINT = "http://localhost:8000/process_audio"
API_ENDPOINT = os.getenv("URL") + "/process_audio"
# API_ENDPOINT="https://817df3966e64.ngrok-free.app/process_audio"
SAMPLERATE = 44100
CHANNELS = 1  # mono


def tts_to_bytes(text):
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    for v in voices:
        if "female" in v.name.lower() or "zira" in v.name.lower():
            engine.setProperty("voice", v.id)
            break
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp_path = tmp.name
    engine.save_to_file(text, tmp_path)
    engine.runAndWait()
    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()
    os.remove(tmp_path)
    return audio_bytes

def play_audio_bytes(audio_bytes):
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    audio_html = f"""
    <audio autoplay>
        <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
        Your browser does not support the audio element.
    </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)


# Placeholder to hold pending audio (to play after layout render)
st.session_state.audio_to_play = st.session_state.get("audio_to_play", None)



st.markdown(
    """
    <style>
    html, body {
        margin: 0;
        padding: 0;
        height: 100%;
    }
    body {
       background: linear-gradient(135deg, #C3B1E1, #F5F0F8, #E1C3E1);
        background-attachment: fixed;
    }

    .stApp {
        background-color: transparent;
        min-height:100vh;
    }
    </style>
    """,
    unsafe_allow_html=True
)


st.set_page_config(page_title="Empathia: Your Personal Therapist", page_icon="🧠", layout="centered")

st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {visibility: hidden;}
    .block-container {padding-top: 0rem;}
    </style>
    """,
    unsafe_allow_html=True
)


st.markdown(
    """
    <div style="
        background-color: #C3B1E1;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    ">
        <h1 style="
            color: #ffffff;
            font-family: 'Arial', sans-serif;
            margin: 0;
        ">🧠 EMPATHIA</h1>
        <h2 style="
            color: #ffffff;
            font-family: 'Arial', sans-serif;
            margin: 0;
        ">Your Personal Therapist</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "recording" not in st.session_state:
    st.session_state.recording = False
if "stream" not in st.session_state:
    st.session_state.stream = None
if "audio_queue" not in st.session_state:
    st.session_state.audio_queue = None
# --- Prevent accidental re-trigger of audio processing ---
if "skip_audio_processing" not in st.session_state:
    st.session_state.skip_audio_processing = False
if "processed_audio_once" not in st.session_state:
    st.session_state.processed_audio_once = False
if "awaiting_helpline_response" not in st.session_state:
    st.session_state.awaiting_helpline_response = False
if "helpline_prompt_played" not in st.session_state:
    st.session_state.helpline_prompt_played = False
if "hide_last_assistant_msg" not in st.session_state:
    st.session_state.hide_last_assistant_msg = False
# --- Mic state initialization (fix for recorder after reload) ---
if "mic_ready" not in st.session_state:
    st.session_state.mic_ready = True
if "mic_reinit_pending" not in st.session_state:
    st.session_state.mic_reinit_pending = False





# --- Helpline Mode Lockdown ---
if st.session_state.get("awaiting_helpline_response", False):
    st.warning("⚠️ It sounds like you're going through a tough time.")
    st.info("Would you like to contact a suicide prevention helpline now?")

    # 🔊 Play the helpline TTS message once
    if not st.session_state.helpline_prompt_played:
        helpline_text = "It seems you are going through a tough time. Would you like to contact a suicide prevention helpline now?"
        helpline_audio = tts_to_bytes(helpline_text)
        audio_b64 = base64.b64encode(helpline_audio).decode("utf-8")
        st.markdown(
            f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
            </audio>
            """,
            unsafe_allow_html=True
        )
        st.session_state.helpline_prompt_played = True

    # 📱 Ask for phone number
    st.session_state.user_phone = st.text_input(
        "📱 Enter your phone number (with country code):",
        value=st.session_state.user_phone or "+91",
        help="Example: +919876543210",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📞 Yes, connect me", use_container_width=True):
            st.session_state.skip_audio_processing = True
            st.session_state.pending_audio = None
            st.session_state.awaiting_helpline_response = False
            st.session_state.helpline_prompt_played = False  # reset for future sessions
            st.session_state.hide_last_assistant_msg = True  # permanently hide last message
            if not st.session_state.user_phone.strip() or not st.session_state.user_phone.startswith("+"):
                st.error("⚠️ Please enter a valid phone number with country code (e.g., +91XXXXXXXXXX).")
            else:
                st.session_state.helpline_requested = True
                st.rerun()


    with col2:
        if st.button("❌ No, not now", use_container_width=True):
            # st.info("You chose not to connect right now. Remember, help is always available ❤️")
            st.session_state.awaiting_helpline_response = False
            st.session_state.helpline_prompt_played = False
            st.session_state.suicide_check = "no"
            st.session_state.hide_last_assistant_msg = False

            # 👇 Generate and store the audio for playback
            if st.session_state.messages:
                last_msg = st.session_state.messages[-1]["content"]
                audio_bytes = tts_to_bytes(last_msg)
                st.session_state.audio_to_play_after_decline = base64.b64encode(audio_bytes).decode("utf-8")

            # Don’t rerun here — allow current render to complete
            st.rerun()


    # 🚫 Stop all other code from running until user decides
    st.stop()



st.markdown(
    """
    <style>
    .recording-dot {
        display:inline-block;
        margin-right:8px;
        height:12px;
        width:12px;
        border-radius:50%;
        background:red;
        -webkit-animation: blink 1s infinite;
        animation: blink 1s infinite;
    }
    div.stButton > button:first-child {
        width: 720px;
        padding: 12px;
        border-radius: 10px;
        font-size: 18px;
        font-weight: bold;
    }
    .chat-container {
        max-height: 400px;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 10px;
        background-color: #f9f9f9;
    }
    .user-msg {
        background-color: #DCF8C6;
        padding: 8px 12px;
        border-radius: 10px;
        margin: 5px 0;
        text-align: right;
    }
    .agent-msg {
        background-color: #E6E6FA;
        padding: 8px 12px;
        border-radius: 10px;
        margin: 5px 0;
        text-align: left;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("""
<style>
/* 🎤 Make mic recorder buttons look identical to Streamlit buttons */
div[data-testid="stMicRecorder"] button {
    width: 720px !important;
    padding: 12px !important;
    border-radius: 10px !important;
    font-size: 18px !important;
    font-weight: bold !important;
    background-color: #C3B1E1 !important;  /* Same lavender */
    color: white !important;
    border: none !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
}

/* Hover effect same as Clear Chat */
div[data-testid="stMicRecorder"] button:hover {
    background-color: #b39ddb !important;
    transform: scale(1.02);
}

/* Active press effect */
div[data-testid="stMicRecorder"] button:active {
    background-color: #9c88d0 !important;
    transform: scale(0.98);
}

/* Optional: make both buttons uniform */
div.stButton > button, div[data-testid="stMicRecorder"] button {
    width: 720px !important;
}
</style>
""", unsafe_allow_html=True)




# st.markdown("### 🎤 Record Your Voice")

# If a reinit is pending, rebuild mic and reset flag
if st.session_state.mic_reinit_pending:
    st.session_state.mic_ready = True
    st.session_state.mic_reinit_pending = False


audio = None
if (
    st.session_state.get("mic_ready", True)
    and not st.session_state.get("helpline_requested", False)
    and not st.session_state.get("call_in_progress", False)
):
    audio = mic_recorder(
        start_prompt="🎙️ Say Something",
        stop_prompt="⏹️ Stop Recording",
        just_once=False,
        use_container_width=True,
        format="wav",
    )




if audio and "pending_audio" not in st.session_state:
    st.session_state.pending_audio = BytesIO(audio["bytes"])
    st.session_state.processed_audio_once = False




# suicide_check = st.session_state.get("suicide_check", "no")

# Placeholder for audio HTML
audio_html_container = ""


# Process pending audio
if (
    "pending_audio" in st.session_state
    and st.session_state.pending_audio is not None
    and not st.session_state.skip_audio_processing
    and not st.session_state.processed_audio_once
    and not st.session_state.get("awaiting_helpline_response", False)
):
    audio_buffer = st.session_state.pending_audio
    del st.session_state.pending_audio
    st.session_state.processed_audio_once = True


    # st.audio(audio_buffer, format="audio/wav")
    # st.session_state.messages.append({"role": "user", "content": "🎤 (voice message sent)"})

    try:
        # files = {"file": ("user_audio.mp3", audio_buffer.getvalue(), "audio/mpeg")}
        files = {"file": ("user_audio.wav", audio_buffer.getvalue(), "audio/wav")}
        with st.spinner("Thinking and generating response..."):
            response = requests.post(API_ENDPOINT, files=files, timeout=120)

        if response.status_code == 200:
            user_query = response.json().get("query", "🎤 (voice message sent)")
            st.session_state.messages.append({"role": "user", "content": user_query})
            response_text = response.json().get("response_text", "")
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            suicide_check = response.json().get("suicide_check", "no")
            st.session_state.suicide_check = suicide_check
            if suicide_check.strip().lower() == "yes":
                st.session_state.awaiting_helpline_response = True
                st.session_state.hide_last_assistant_msg = True  # temporarily hide last bot message
                st.rerun()




            audio_bytes = tts_to_bytes(response_text)
            if audio_bytes and len(audio_bytes) > 1000:
                # Store audio bytes for post-render playback
                st.session_state.audio_to_play = base64.b64encode(audio_bytes).decode("utf-8")

            # 🚨 If suicidal signs detected, ask for consent to call
        else:
            st.error(f"API request failed: status {response.status_code}")
    except Exception as e:
            st.error(f"Error contacting API: {e}")


# --- Suicide Helpline Call Section ---
if "helpline_requested" not in st.session_state:
    st.session_state.helpline_requested = False
if "call_in_progress" not in st.session_state:
    st.session_state.call_in_progress = False
if "user_phone" not in st.session_state:
    st.session_state.user_phone = ""



# --- Trigger API Call Once ---
# if st.session_state.get("helpline_requested") and not st.session_state.get("call_in_progress", False):
#     st.session_state.call_in_progress = True
#     st.write("🕓 Initiating call... please wait.")

#     try:
#         with st.spinner("Connecting to helpline..."):
#             api_response = requests.post(
#                 os.getenv("URL") + "/call_helpline",
#                 json={"to_number": st.session_state.user_phone},
#                 timeout=30
#             )

#         if api_response.status_code == 200:
#             data = api_response.json()
#             st.success("✅ Calling the suicide helpline. Please hold on…")
#             st.info(f"Call SID: {data.get('call_sid', 'N/A')}")
#         else:
#             st.error(f"❌ Failed to initiate call. Server responded with: {api_response.status_code}")
#             st.error(api_response.text)

#     except requests.exceptions.ConnectionError:
#         st.error("🚫 Unable to reach the helpline service. Please ensure your backend is running.")

#     except requests.exceptions.Timeout:
#         st.error("⏱️ Request timed out. The helpline service took too long to respond.")

#     except Exception as e:
#         st.error(f"❌ Unexpected error: {e}")

#     finally:
#         st.session_state.helpline_requested = False
#         st.session_state.call_in_progress = False
#         st.session_state.skip_audio_processing = False

#         # ✅ Mark mic to reinitialize
#         st.session_state.mic_reinit_pending = True
#         st.success("✅ Helpline call finished. You can continue speaking now!")

#         # Rerun to rebuild mic component
#         st.rerun()

# --- Trigger API Call Once ---
if st.session_state.get("helpline_requested") and not st.session_state.get("call_in_progress", False):
    st.session_state.call_in_progress = True

    try:
        with st.spinner("Connecting to helpline..."):
            api_response = requests.post(
                os.getenv("URL") + "/call_helpline",
                json={"to_number": st.session_state.user_phone},
                timeout=30
            )

        if api_response.status_code == 200:
            st.session_state.helpline_connected = True  # ✅ mark connected
        else:
            st.error(f"❌ Failed to initiate call. Server responded with: {api_response.status_code}")
            st.error(api_response.text)
            st.session_state.helpline_connected = False

    except requests.exceptions.ConnectionError:
        st.error("🚫 Unable to reach the helpline service. Please ensure your backend is running.")
        st.session_state.helpline_connected = False

    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. The helpline service took too long to respond.")
        st.session_state.helpline_connected = False

    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        st.session_state.helpline_connected = False

    finally:
        st.session_state.helpline_requested = False
        st.session_state.call_in_progress = False
        st.session_state.skip_audio_processing = True  # prevent further audio
        st.session_state.mic_ready = False             # disable mic
        st.session_state.mic_reinit_pending = False
        st.rerun()


# --- Show message after helpline connection ---
if st.session_state.get("helpline_connected", False):
    st.markdown(
        """
        <div style='
            background-color:#f0f0ff;
            padding:20px;
            border-radius:10px;
            text-align:center;
            font-size:18px;
            font-family:Arial;
            color:#4b0082;
        '>
        <p>📞 You'll receive a call from the suicide prevention helpline on your provided phone number.</p>
        <p>🔄 To continue the chat, please reload the page.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Show only clear chat button, hide everything else
    if st.button("🧹 Clear Chat"):
        try:
            requests.post(os.getenv("URL") + "/reset", timeout=5)
        except Exception:
            pass
        st.session_state.clear()
        st.success("✅ Chat cleared successfully! Reload to start again.")
    st.stop()  # 🚫 stop further UI (hide mic, etc.)



# 🧹 Clear Chat Section (Safe Reset — keeps mic working)
if st.button("🧹 Clear Chat"):
    try:
        # Reset backend conversation if applicable
        try:
            requests.post(os.getenv("URL") + "/reset", timeout=5)
        except Exception:
            pass  # optional backend reset

        # Only clear relevant local state — don't rerun or reload the page
        st.session_state.messages = []
        st.session_state.audio_to_play = None
        st.session_state.audio_to_play_after_decline = None
        st.session_state.suicide_check = "no"
        st.session_state.awaiting_helpline_response = False
        st.session_state.helpline_prompt_played = False
        st.session_state.hide_last_assistant_msg = False

        # Optional: show confirmation
        st.success("✅ Chat cleared successfully! You can start fresh now.")

    except Exception as e:
        st.error(f"Could not reset history: {e}")




# ------------------ Chat history ------------------
if st.session_state.messages:
    st.markdown("### Conversation")
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    # If the assistant message should be hidden, skip it from display
    messages_to_show = st.session_state.messages.copy()
    if st.session_state.hide_last_assistant_msg and messages_to_show:
        if messages_to_show[-1]["role"] == "assistant":
            messages_to_show[-1] = {
            "role": "assistant",
            "content": "📞 Calling suicide helpline… please wait.",
        }

    for msg in messages_to_show[::-1]:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="agent-msg">{msg["content"]}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ✅ Play stored audio invisibly after full layout render
if st.session_state.get("audio_to_play"):
    audio_b64 = st.session_state.audio_to_play

    st.markdown(
        f"""
        <audio id="hiddenAudio" autoplay>
            <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
        </audio>

        <script>
        // fallback: ensure playback even if autoplay is blocked
        const audioElement = document.getElementById("hiddenAudio");

        audioElement.play().catch(err => {{
            console.warn("Autoplay blocked 😕 — waiting for user click...");
            const resumePlayback = () => {{
                audioElement.play().then(() => {{
                    console.log("Playback resumed ✅");
                    document.removeEventListener("click", resumePlayback);
                    document.removeEventListener("keydown", resumePlayback);
                }}).catch(e => console.error("Playback still blocked:", e));
            }};
            document.addEventListener("click", resumePlayback);
            document.addEventListener("keydown", resumePlayback);
        }});
        </script>
        """,
        unsafe_allow_html=True
    )

    # Clear after playback so it doesn't repeat
    st.session_state.audio_to_play = None

# 🎧 Handle playback for "No, not now" response
if st.session_state.get("audio_to_play_after_decline"):
    audio_b64 = st.session_state.audio_to_play_after_decline

    st.markdown(
        f"""
        <audio id="declineAudio" autoplay>
            <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
        </audio>

        <script>
        const audio = document.getElementById("declineAudio");
        audio.addEventListener('ended', function() {{
            console.log("Audio finished — rerunning Streamlit app.");
            fetch(window.location.href, {{method: "POST"}}).then(() => {{
                window.parent.location.reload();
            }});
        }});
        </script>
        """,
        unsafe_allow_html=True
    )

    # clear it so it doesn't replay on next rerun
    st.session_state.audio_to_play_after_decline = None

