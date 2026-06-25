from fastapi import FastAPI, UploadFile, File, HTTPException,Form
from fastapi import BackgroundTasks
import os
from predict import emotions
from chatbot import voice_agent_reply,conversation_history
from pydub import AudioSegment
import io
import logging
from chatbot import update_history
from dotenv import load_dotenv
from pydantic import BaseModel
from twilio.rest import Client
from fastapi.responses import Response

load_dotenv()

logging.basicConfig(filename="logfile.txt",level=logging.INFO,format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI()

UPLOAD_DIR = "uploaded_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)
FIXED_FILENAME = "user_audio.wav"

@app.get('/')
def home_endpoint():
    return {'message':'Welcome to Empathia API'}

@app.get('/health')
def health_check():
    return {'status':'OK'}

# @app.post("/process_audio")
# async def process_audio(file: UploadFile = File(...)):
#     if not file.filename.endswith(".wav"):
#         raise HTTPException(status_code=400, detail="Only WAV files are supported.")
#     print("File is in WAV format")
#     save_path = os.path.join(UPLOAD_DIR, FIXED_FILENAME)

#     try:
#         contents = await file.read()
#         with open(save_path, "wb") as f:
#             f.write(contents)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
#     print("read file")
#     try:
#         emotion_result = emotions(save_path)
#         print("Emotions detected")
#         chain_result = voice_agent_reply(emotion_result)
#         print("Reply generated")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing chain: {e}")

#     return {"query":emotion_result['query'],"response_text": chain_result}

# @app.post("/process_audio")
# async def process_audio(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
#     if not file.filename.endswith(".wav"):
#         raise HTTPException(status_code=400, detail="Only WAV files are supported.")
#     save_path = os.path.join(UPLOAD_DIR, FIXED_FILENAME)

#     try:
#         contents = await file.read()
#         with open(save_path, "wb") as f:
#             f.write(contents)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

#     try:
#         # Step 1: Detect emotions from the audio
#         emotion_result = emotions(save_path)

#         # Step 2: Generate chatbot response
#         chain_result = voice_agent_reply(emotion_result)

#         # Step 3: Update conversation history in the background
#         from chatbot import update_history
#         background_tasks.add_task(update_history, emotion_result['query'], chain_result)

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing chain: {e}")

#     # Step 4: Return response immediately
#     return {
#         "query": emotion_result['query'],
#         "response_text": chain_result
#     }

# @app.post("/process_audio")
# async def process_audio(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
#     if not file.filename.endswith(".wav"):
#         raise HTTPException(status_code=400, detail="Only WAV files are supported.")

#     try:
#         contents = await file.read()  
#         emotion_result = emotions(contents) 
#         chain_result = voice_agent_reply(emotion_result)

#         # Update conversation history in background
#         from chatbot import update_history
#         background_tasks.add_task(update_history, emotion_result['query'], chain_result)

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing chain: {e}")

#     return {
#         "query": emotion_result['query'],
#         "response_text": chain_result
#     }

# @app.post("/process_audio")
# async def process_audio(file: UploadFile = File(...)):
#     if not file.filename.endswith(".wav"):
#         raise HTTPException(status_code=400, detail="Only WAV files are supported.")

#     # Save the uploaded file efficiently to a temporary location
#     temp_path = f"uploaded_audio/{file.filename}"
#     with open(temp_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)  # Efficient streaming copy

#     # Read file into memory only if emotions() requires bytes
#     with open(temp_path, "rb") as f:
#         contents = f.read()

#     # Call your dummy processing functions
#     emotion_result = emotions(contents)   # returns a dummy string or dict
#     chain_result = voice_agent_reply(emotion_result)

#     return {
#         "query": emotion_result['query'],
#         "response_text": chain_result
#     }

# @app.post("/process_audio")
# async def process_audio(file: UploadFile = File(...),background_tasks: BackgroundTasks = None):
#     logging.info("API call made for process_audio")

#     if not (file.filename.endswith(".wav") or file.filename.endswith(".mp3")):
#         raise HTTPException(status_code=400, detail="Only WAV or MP3 files are supported.")


#     contents = await file.read()
#     logging.info("Read uploaded file into memory")
    
#     if file.filename.endswith(".mp3"):
#         audio_segment = AudioSegment.from_file(io.BytesIO(contents), format="mp3")
#         wav_io = io.BytesIO()
#         audio_segment.export(wav_io, format="wav")
#         wav_io.seek(0)
#         contents = wav_io.read() 
#         logging.info("Converted to wav")
#     try:
#         emotion_result = emotions(contents)  
#         logging.info("Fetched emotion results")
#     except Exception as e:
#         raise HTTPException(status_code=500,detail=f"Error processing emotions:{e}")
#     try:
#         chain_result = voice_agent_reply(emotion_result)
#         logging.info("fetched chain result")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing chain: {e}")

#     if background_tasks is not None:
#         background_tasks.add_task(update_history, emotion_result['query'], chain_result)
#         logging.info("Scheduled conversation history update in background")
#     return {
#         "query": emotion_result['query'],
#         "response_text": chain_result['response'],
#         "suicide_check":chain_result['suicide_check']
#     }

@app.post("/reset")
def reset_history():
    global conversation_history
    conversation_history.clear()
    return {"status": "history cleared"}


@app.post("/process_audio")
async def process_audio(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    logging.info("API call made for process_audio")

    if not file.filename.endswith(".wav"):
        raise HTTPException(status_code=400, detail="Only WAV files are supported.")

    contents = await file.read()
    logging.info(f"Read uploaded WAV file ({len(contents)} bytes)")

    try:
        AudioSegment.from_file(io.BytesIO(contents), format="wav")
        logging.info("✅ WAV file verified")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error decoding WAV: {e}")

    try:
        emotion_result = emotions(contents)
        logging.info("Fetched emotion results")
        chain_result = voice_agent_reply(emotion_result)
        logging.info("Fetched chain result")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing: {e}")

    if background_tasks:
        background_tasks.add_task(update_history, emotion_result['query'], chain_result)

    return {
        "query": emotion_result['query'],
        "response_text": chain_result['response'],
        "suicide_check": chain_result['suicide_check']
    }






class CallRequest(BaseModel):
    to_number: str  # phone number to call

# @app.post("/call_helpline")
# async def call_helpline(req: CallRequest):
#     try:
#         client = Client(
#             os.getenv("TWILIO_ACCOUNT_SID"),
#             os.getenv("TWILIO_AUTH_TOKEN")
#         )

#         call = client.calls.create(
#             to=req.to_number,
#             from_=os.getenv("TWILIO_FROM_NUMBER"),
#             url="http://demo.twilio.com/docs/voice.xml"  # You can replace this with a custom TwiML URL
#         )

#         return {"status": "success", "call_sid": call.sid}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.post("/call_helpline")
async def call_helpline(req: CallRequest):
    try:
        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )

        helpline_number = os.getenv("HELPLINE_NUMBER")  # e.g. "+18001234567"

        # Step 1: Create a unique conference name
        conference_name = f"helpline_conf_{req.to_number[-4:]}"

        # Step 2: Call the user first
        user_call = client.calls.create(
            to=req.to_number,
            from_=os.getenv("TWILIO_FROM_NUMBER"),
            url=f"{os.getenv('BASE_URL')}/twiml/user_join_conference?conf_name={conference_name}"
        )

        

        # Step 3: Call the helpline second
        helpline_call = client.calls.create(
            to=helpline_number,
            from_=os.getenv("TWILIO_FROM_NUMBER"),
            url=f"{os.getenv('BASE_URL')}/twiml/helpline_join_conference?conf_name={conference_name}"
        )

        return {
            "status": "success",
            "call_sid": user_call.sid,
            "helpline_call_sid": helpline_call.sid,
            "conference_name": conference_name
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@app.post("/twiml/user_join_conference")
async def user_join_conference(conf_name: str):
    twiml = f"""
    <Response>
        <Say voice="alice">Your call is being connected, please wait.</Say>
        <Pause length="2"/>
        <Dial>
            <Conference startConferenceOnEnter="true" endConferenceOnExit="true">{conf_name}</Conference>
        </Dial>
    </Response>
    """
    return Response(content=twiml.strip(), media_type="application/xml")


@app.post("/twiml/helpline_join_conference")
async def helpline_join_conference(conf_name: str):
    twiml = f"""
    <Response>
        <Dial>
            <Conference startConferenceOnEnter="true" endConferenceOnExit="true">{conf_name}</Conference>
        </Dial>
    </Response>
    """
    return Response(content=twiml.strip(), media_type="application/xml")
