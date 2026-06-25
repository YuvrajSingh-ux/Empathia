from faster_whisper import WhisperModel
from speech_classifier import predict_speech
from text_classifier import predict_text
import os
import torch
import io

model = WhisperModel("tiny.en", device="cuda" if torch.cuda.is_available() else "cpu", compute_type="int8")


# def emotions(filepath):
#     speech_emotion=predict_speech(filepath)
#     segments, info = model.transcribe(filepath,beam_size=1,language="en",without_timestamps=True)
#     text=" ".join([s.text for s in segments]).strip()
#     text_emotion=predict_text(text)
#     return {'speech_emotions':speech_emotion,'text_emotions':text_emotion,'query':text}

def emotions(file_bytes:bytes):
    speech_emotion=predict_speech(file_bytes)
    audio_buffer = io.BytesIO(file_bytes)
    segments, info = model.transcribe(audio_buffer,beam_size=1,language="en",without_timestamps=True)
    text=" ".join([s.text for s in segments]).strip()
    text_emotion=predict_text(text)
    return {'speech_emotions':speech_emotion,'text_emotions':text_emotion,'query':text}