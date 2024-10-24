#################
#### IMPORTS ####
#################
from datetime import date, datetime
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
def generate_response(question, sessions_data, items_data):
    prompt = """
    You are a helpful assistant on {todays_date} who has access to a database of process sessions and the items they have processed.
    Here is the data for the processes sessions: {sessions_data}
    It contains information about the process name, process status, process session start time and process session end time.
    The process status can be 'running', 'stopped', 'completed' and 'terminated'. Here are some rules:
    A process is completed when the 'process_status' column contains the value 'Completed'.
    A process is currently running when the 'process_status' column contains the value 'Running'.
    A process failed when the 'process_status' column contains the value 'Terminated'.
    Here is the data for the items processed during the provided process sessions above: {items_data}
    It contains information about the item name, the name of the process that processed it and the workqueue name where it is stored.
    Here are some rules for the items.
    A 'process_name' can have one or more 'workqueue_name'.
    Each 'workqueue_name' can have one or more 'item_key'.
    Each item belongs to one single 'workqueue_name'.
    An item is completed when the 'completed' column is not empty.
    An item is an exception when the 'exception' column is not empty.
    Answer the following question based on the database information.
    {user_question}
    """

    response = model.generate_content(
        prompt.format(
            user_question=question,
            sessions_data=sessions_data,
            items_data=items_data,
            todays_date=date.today(),
        )
    )
    return response.text


# Transforms the text to voice
def speak_text(text):
    engine.say(text)
    engine.runAndWait()


# Get the latest data from the database
def get_process_sessions():
    query = """
        SELECT
            BPAProcess.name as process_name,
            BPAStatus.description as status,
            BPASession.startdatetime as start_time,
            BPASession.enddatetime as end_time
        FROM BPASession
            INNER JOIN BPAProcess on BPASession.processid = BPAProcess.processid
            INNER JOIN BPAStatus on BPASession.statusid = BPAStatus.statusid
        WHERE BPAProcess.ProcessType = 'P'
            AND BPAStatus.description IN ('Completed', 'Running', 'Terminated', 'Stopped')
            AND BPASession.startdatetime >= DATEADD(day, -7, GETDATE())
    """
    cursor.execute(query)
    query_output = cursor.fetchall()
    sessions = list()
    for session in query_output:
        sessions.append(
            {
                "process_name": session[0],
                "process_status": session[1],
                "process_start_time": session[2],
                "process_end_time": session[3],
            }
        )
    return sessions


def get_items():
    query = """
        SELECT
            BPVWorkQueueItem.keyvalue as item_key,
            bpaProcess.name as process_name,
            BPAProcessQueueDependency.refQueueName as queue_name,
            BPVWorkQueueItem.completed,
            BPVWorkQueueItem.exception
        FROM
            BPAProcessQueueDependency
            inner join BPAProcess on BPAProcessQueueDependency.processID = BPAProcess.processid
            inner join BPAWorkQueue on BPAWorkQueue.name = BPAProcessQueueDependency.refQueueName
            inner join BPVWorkQueueItem on BPVWorkQueueItem.queueid = BPAWorkQueue.id
        WHERE
            BPVWorkQueueItem.loaded >= DATEADD(day, -7, GETDATE())
    """
    cursor.execute(query)
    query_output = cursor.fetchall()
    items = list()
    for item in query_output:
        items.append(
            {
                "item_name": item[0],
                "process_name": item[1],
                "workqueue_name": item[2],
                "completed_date": item[3],
                "exception_date": item[4],
            }
        )
    return items


def notify_terminations(end_date_time):
    output = ""
    query = """
            SELECT
                BPAProcess.name as process_name
            FROM BPASession
                INNER JOIN BPAProcess on BPASession.processid = BPAProcess.processid
                INNER JOIN BPAStatus on BPASession.statusid = BPAStatus.statusid
            WHERE BPAProcess.ProcessType = 'P'
                AND BPAStatus.description = 'Terminated'
                AND BPASession.enddatetime >= ?
            """

    cursor.execute(query, end_date_time)
    query_output = cursor.fetchall()
    if len(query_output) == 0:
        output = end_date_time
    elif len(query_output) == 1:
        speak_text(
            "Hey bro, the process named '" + query_output[0][0] + "' has terminated."
        )
        output = datetime.now()
    else:
        processes = ""
        for row in query_output:
            processes = processes + row[0] + ", "
        speak_text("Hey, processes '" + processes + "'")
        output = datetime.now()

    return output


######################
#### MAIN ROUTINE ####
######################


if __name__ == "__main__":
    ##### SETUP #####
    startup = datetime.now()
    last_check = startup

    # What to say to have Gemini listening
    trigger_command = "hey"
    stop_command = "exit"

    while True:
        # Wait for user to say "hey"
        print(
            f"Say '{trigger_command}' to start recording your question or {stop_command} to stop the program."
        )
        # CHECK HERE FOR TERMINATIONS AND NOTIFY THEM BY AUDIO
        last_check = notify_terminations(last_check)
        with sr.Microphone() as source:
            recognizer = sr.Recognizer()
            audio = ""
            try:
                audio = recognizer.listen(source, timeout=5)
            except:
                print("Waiting...")
            if audio:
                try:
                    transcription = recognizer.recognize_google(audio)
                    if transcription.lower() == trigger_command:
                        # Get user answer
                        filename = "input.wav"
                        print("Ask your question...")
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
                            # Get latests session info from database
                            sessions = get_process_sessions()
                            items = get_items()
                            # Get model response
                            response = generate_response(text, sessions, items)
                            print("Response: " + response)
                            speak_text(response)
                    elif transcription.lower() == stop_command:
                        print("See you later! :)")
                        speak_text("See you later!")
                        break
                except Exception as e:
                    print("An error occurred: {}".format(e))

# Close database connection
conn.close()
