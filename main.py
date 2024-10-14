import configparser
import google.generativeai as genai  # AI
import pyttsx3  # Text to speech
import speech_recognition as sr  # Speech to text


def transcribe_audio_to_text(filename):
    recognizer = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio)
    except:
        print("Skipping unknown error.")


def generate_response(model, prompt):
    response = model.generate_content(prompt)
    return response.text


def speak_text(engine, text):
    engine.say(text)
    engine.runAndWait()


if __name__ == "__main__":
    ##### SETUP #####

    trigger_sentence = "hey"

    # Get API Key
    cfg_file = configparser.ConfigParser()
    cfg_file.read("config\setup.ini")
    api_key = cfg_file["GOOGLE_AI"]["api_key"]

    # Configure API Key
    genai.configure(api_key=api_key)

    # Model configuration
    model_config = {
        "temperature": 0.5,
        "top_p": 0.99,
        "top_k": 0,
        "max_output_tokens": 2000,
    }

    ##### INIT #####

    # AI Model init
    model = genai.GenerativeModel(
        "gemini-1.5-flash-latest", generation_config=model_config
    )

    # text-to-speech engine init
    engine = pyttsx3.init()

    while True:
        # Wait for user to say "genius"
        print(f"Say '{trigger_sentence}' to start recording your question...")
        with sr.Microphone() as source:
            recognizer = sr.Recognizer()
            audio = recognizer.listen(source)
            try:
                transcription = recognizer.recognize_google(audio)
                if transcription.lower() == trigger_sentence:
                    filename = "input.wav"
                    print("Say your question...")
                    with sr.Microphone() as source:
                        recognizer = sr.Recognizer()
                        source.pause_threshold = 1
                        audio = recognizer.listen(
                            source, phrase_time_limit=None, timeout=None
                        )
                        with open(filename, "wb") as f:
                            f.write(audio.get_wav_data())
                    text = transcribe_audio_to_text(filename)
                    if text:
                        print(f"You said: {text}")
                        response = generate_response(model, text)
                        print("Response: " + response)
                        speak_text(engine, response)
            except Exception as e:
                print("An error occurred: {}".format(e))
