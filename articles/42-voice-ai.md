---
title: "Voice AI: Building Multilingual Dialog Systems with ElevenLabs"
description: "Production-grade technical deep-dive on VoiceAI:BuildingMultilingualDialogSystemswithElevenLabs"
keywords: ["42-voice-ai"]
author: "Pratik Dhanave"
date: "2026-06-04"
readtime: "10-15 min"
---

# Voice AI: Building Multilingual Dialog Systems with ElevenLabs

**Voice is the future of customer interaction.** Typing is friction. Speaking is natural. But building voice assistants at scale (multi-language, real-time, reliable) is hard.

Kinetic India's voice assistant handles 10K+ two-wheeler riders asking about vehicle diagnostics, service bookings, and ride telemetry — all in Hindi, English, and regional languages.

---

## The Voice AI Pipeline

```
User Speech
    ↓
Speech-to-Text (STT)
    ↓
Intent Recognition (LLM)
    ↓
Context Lookup (RAG)
    ↓
Response Generation (LLM)
    ↓
Text-to-Speech (TTS) via ElevenLabs
    ↓
User Hears Response
```

---

## Speech-to-Text: Handling Accents and Noise

```python
from google.cloud import speech_v1

def transcribe_audio(audio_file: str, language_code: str = "hi-IN"):
    """Convert audio to text with accent handling."""
    client = speech_v1.SpeechClient()
    
    with open(audio_file, "rb") as audio:
        content = audio.read()
    
    audio = speech_v1.RecognitionAudio(content=content)
    config = speech_v1.RecognitionConfig(
        encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language_code,
        enable_automatic_punctuation=True,
        model="latest_long",  # Better for noisy environments
    )
    
    response = client.recognize(config=config, audio=audio)
    
    if response.results:
        return response.results[0].alternatives[0].transcript
    return ""
```

---

## Intent Recognition + Context

```python
from anthropic import Anthropic

class DialogueManager:
    def __init__(self):
        self.client = Anthropic()
        self.conversation_history = []
    
    def process_user_input(self, user_text: str, language: str):
        """Understand intent and context."""
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_text,
        })
        
        # Get response from Claude (understands Hindi, English, regional languages)
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            system=f"""You are a helpful voice assistant for a two-wheeler service app.
            Language: {language}
            Available actions: check_vehicle_health, book_service, get_ride_stats
            
            Respond naturally and briefly (max 2 sentences). Confirm understanding.""",
            messages=self.conversation_history,
        )
        
        assistant_response = response.content[0].text
        
        # Add response to history for next turn
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_response,
        })
        
        return assistant_response

# Usage
manager = DialogueManager()
response = manager.process_user_input("मेरी बाइक का तेल कब बदलना है?", "hi-IN")
# Response: "आपकी बाइक का तेल आगले 2000 किमी में बदलना है।"
```

---

## Text-to-Speech: ElevenLabs for Natural Voice

```python
import elevenlabs
from elevenlabs.client import ElevenLabs

def synthesize_speech(text: str, language: str = "hi"):
    """Generate natural-sounding speech."""
    client = ElevenLabs(api_key="...")
    
    # Choose voice by language
    voice_map = {
        "hi": "Nutan",  # Hindi voice
        "en": "Bella",  # English voice
        "ta": "Isha",   # Tamil voice
    }
    
    audio = client.generate(
        text=text,
        voice=voice_map.get(language, "Bella"),
        model="eleven_multilingual_v2",
        stream=True,  # Stream for low latency
    )
    
    # Play audio in real-time
    for chunk in audio:
        play_audio_chunk(chunk)

# Usage
response = "आपकी बाइक का तेल आगले 2000 किमी में बदलना है।"
synthesize_speech(response, language="hi")
# User hears natural Hindi speech
```

---

## Multi-Turn Conversation State

```python
class VoiceSession:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.conversation_turns = []
        self.context = {}  # Vehicle info, preferences
    
    def handle_turn(self, audio_file: str) -> str:
        """One full turn: hear, understand, respond."""
        
        # 1. Transcribe
        user_text = transcribe_audio(audio_file)
        
        # 2. Understand intent
        manager = DialogueManager()
        response = manager.process_user_input(user_text, language="hi")
        
        # 3. Generate speech
        synthesize_speech(response, language="hi")
        
        # 4. Save turn
        self.conversation_turns.append({
            "user": user_text,
            "assistant": response,
            "timestamp": datetime.now(),
        })
        
        return response

# Usage: Multi-turn conversation
session = VoiceSession(user_id="RIDER-123")
session.handle_turn("audio_1.wav")  # "मेरी बाइक का तेल कब बदलना है?"
session.handle_turn("audio_2.wav")  # "ठीक है, मुझे सर्विस बुक करना है"
```

---

**Tags:** #VoiceAI #SpeechRecognition #MultiLanguage #ElevenLabs #Dialog

**Published:** June 2026  
**Author:** Pratik Dhanave  
**Related Projects:** Kinetic India voice assistant
