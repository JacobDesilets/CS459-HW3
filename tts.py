import sys
from gtts import gTTS
import playsound
import speech_recognition as sr

def textToSpeech(text):
    tts = gTTS(text=text, lang='en')
    filename = "speech.mp3"
    tts.save(filename)
    playsound.playsound(filename)


def speechToText():
    r = sr.Recognizer()
    while(1):
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.2)
                audio = r.listen(source)
                text = r.recognize_google(audio)
                text = text.lower()
                print("Text:", text)
        except sr.RequestError as e:
            print(e)
        except sr.UnknownValueError:
            print("unknown error")

