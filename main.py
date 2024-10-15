#################
#### IMPORTS ####
#################
import configparser
import pyodbc
import google.generativeai as genai  # AI
import pyttsx3  # Text to speech
import speech_recognition as sr  # Speech to text

####################
#### SETUP CODE ####
####################

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
model = genai.GenerativeModel("gemini-1.5-flash-latest", generation_config=model_config)

# text-to-speech engine init
engine = pyttsx3.init()

# Stablish database connection
conn = pyodbc.connect(
    "Driver={driver};Server={server};Database={database};Trusted_Connection=yes;".format(
        driver="SQL Server", server="INRGY_FFT1\SQLEXPRESS", database="local"
    )
)

# Creates database cursor
cursor = conn.cursor()


###############################
#### FUNCTIONS DEFINITIONS ####
###############################


# Uses the input audio file to transform it to text
def transcribe_audio_to_text(filename):
    recognizer = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio)
    except:
        print("Skipping unknown error.")


# Enters gets Gemini answer to the prompt
def generate_response(model, prompt):
    response = model.generate_content(prompt)
    return response.text


# Transforms the text to voice
def speak_text(engine, text):
    engine.say(text)
    engine.runAndWait()


# Get the latest data from the database
def get_updated_data():
    query = "SELECT BPAProcess.name, BPAStatus.description,	BPASession.startdatetime, BPASession.enddatetime FROM BPASession INNER JOIN BPAProcess on BPASession.processid = BPAProcess.processid INNER JOIN BPAStatus on BPASession.statusid = BPAStatus.statusid WHERE BPAProcess.ProcessType = 'P'"
    cursor.execute(query)
    sessions = cursor.fetchall()
    return sessions


######################
#### MAIN ROUTINE ####
######################


if __name__ == "__main__":
    ##### SETUP #####
    # What to say to have Gemini listening
    trigger_command = "hey bot"
    stop_command = "exit"

    test = get_updated_data()

    while True:
        # Wait for user to say "hey"
        print(f"Say '{trigger_command}' to start recording your question...")
        with sr.Microphone() as source:
            recognizer = sr.Recognizer()
            audio = recognizer.listen(source)
            try:
                transcription = recognizer.recognize_google(audio)
                if transcription.lower() == trigger_command:
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
                elif transcription.lower() == stop_command:
                    speak_text(engine, "See you later!")
                    break
            except Exception as e:
                print("An error occurred: {}".format(e))

# Close database connection
conn.close()
