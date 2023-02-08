import tkinter
from tkinter import ttk
import threading
import time
import createRecording
import os
import re
import zipfile

TUTORIAL_INTRO = "Thank you for participating in this study!"
TUTORIAL_OVERVIEW = "The subject of this study is the Spanish 'r' sound. To participate, this \
program will have you record yourself readings 20 different sentences two to four times each. After \
recording each sentence. The program will give you feedback on your pronounciation of the 'r' sound \
and how consistent it is with the 'r' sound used by most native Spanish speakers. This feedback \
isn't perfect; this program can only give its best effort at identifying your pronounciations. If \
possible, please participate in this study in a quiet place with minimal background noise."
TUTORIAL_INSTRUCTION = "Before you begin, please test the audio recording and playback ability \
of the program with the buttons below. Press the record button once to record your voice, and press \
a second time to stop recording. Any subsequent presses of the button should play your recording \
back to you. If this doesn't appear to work, please contact me at cabeck4@wisc.edu. If the button \
does work, you may press the → button below to begin the study."
FIRST_RECORD_INSTRUCTION = "Please record yourself saying the following sentence once:"
LISTEN_BACK_INSTRUCTION = "Now hear a native speaker's pronounciation with the button below, and play back your own with the button above."
FINAL_RECORD_INSTRUCTION = """Please record the sentence again up to 3 times. Stop when you are \
satisfied with your last recording. Only the last recording will be used. You do not need to use \
all 3 attempts. Click → when finished."""
END_SCREEN_INSTRUCTION = "Thank you very much for participating in this study! You may now close the window."
NATIVE_SPEAKER_VOICE_SAMPLES = ["voiceExamples/rec1.wav", "voiceExamples/rec2.wav",
"voiceExamples/rec3.wav", "voiceExamples/rec4.wav", "voiceExamples/rec5.wav", "voiceExamples/rec6.wav",
"voiceExamples/rec7.wav", "voiceExamples/rec8.wav", "voiceExamples/rec9.wav", "voiceExamples/rec10.wav",
"voiceExamples/rec11.wav", "voiceExamples/rec12.wav", "voiceExamples/rec13.wav", "voiceExamples/rec14.wav",
"voiceExamples/rec15.wav", "voiceExamples/rec16.wav", "voiceExamples/rec17.wav", "voiceExamples/rec18.wav",
"voiceExamples/rec19.wav", "voiceExamples/rec20.wav"]
SENTENCE_SAMPLES = ["Tengo muchas comidas para mi familia.",
"Hay topacio y oro en el anillo.",
"Hay un zorro muy bonito nadando en la playa.",
"Todos quisimos un perro como mascota.",
"Corro dos millas todos los días.",
"El carro de mi tío es azul y blanco.",
"Daniel tocaba la guitarra en la banda.",
"Necesito que la caja sea duro.",
"La mostaza es un condimento horrible en la pizza.",
"Hay una gorra azul de tu talla en la mesa.",
"Quiero lechuga y tomate en mi sándwich.",
"El toro está comiendo heno.",
"La mamá mira a su hijo en el tobogán.",
"Mi gato Felix es muy curioso.",
"Me gustaba mi tiempo en el coro de mi colegio.",
"Dibujo algo nuevo en la pizarra cada semana.",
"Veo una jarra llena de limonada.",
"El juego fue muy caro así que no fuimos.",
"La candela tiene un buen aroma.",
"Veo la cara de una niña en la foto."]
TARGET_WORDS = ["para", "oro", "zorro", "perro", "corro", "carro", "guitarra", "duro",
"horrible", "gorra", "quiero", "toro", "mira", "curioso", "coro", "pizarra", "jarra",
"caro", "aroma", "cara"]
DATA_DIRECTORY = "Please_Send_This_File"
LOG_FILE = "measurementsLog.txt"
logfile = None

# Build the original window and dedicate the main thread to mainloop()
def main():
    root = tkinter.Tk()
    root.config(padx=40, pady=20)

    ttk.Style().configure("TButton", padding=5, relief="flat", font=('Verdana', 10), background="#ccc")
    ttk.Style().configure("TLabel", padding=5, relief="flat", font=('Verdana', 12), anchor='w', wraplength=700)
    ttk.Style().configure("TFrame", anchor='w')
    
    root.geometry("800x800")

    threading.Thread(target=buildWindow, args=(root,)).start()

    root.mainloop()

    try:
        logfile.close()
    except:
        pass

    # TODO Remove all .wav files
    os._exit(0)

# Build a new frame for every phrase
def buildWindow(root):
    makeTutorial(root)

    makePrimaryStudyLoop(root)
    
    buildZippedDataFile()

    makeEndScreen(root)

# Build a screen that provides instructions for the experiment and provides
# two record buttons to test the audio recording functionality
def makeTutorial(parentFrame):
    curFrame = ttk.Frame(parentFrame, padding=(0,0,0,18))
    curFrame.pack(fill=tkinter.BOTH)

    intro = ttk.Label(curFrame, text=TUTORIAL_INTRO, font=('Verdana', 12))
    intro.pack(side=tkinter.TOP, fill=tkinter.BOTH)

    instruction = ttk.Label(curFrame, text=TUTORIAL_INSTRUCTION, font=('Verdana', 12))
    instruction.pack(side=tkinter.TOP, fill=tkinter.BOTH)

    overview = ttk.Label(curFrame, text=TUTORIAL_OVERVIEW, font=('Verdana', 12))
    overview.pack(side=tkinter.TOP, fill=tkinter.BOTH)

    buttonFrame = ttk.Frame(curFrame, padding=(0,18,0,18))
    buttonFrame.pack(fill=tkinter.BOTH)

    buildRecordButton(buttonFrame, "testButton1")
    buildRecordButton(buttonFrame, "testButton2")

    buildNextButton(curFrame)

    # Delete uneeded files if they were created
    try:
        os.remove("testButton1.wav")
    except:
        pass

    try:
        os.remove("testButton2.wav")
    except:
        pass

    curFrame.grid_forget()
    curFrame.destroy()

# Build the series of screens that record the speaker pronouncing
# the given sentences.
def makePrimaryStudyLoop(root):
    instruction = ttk.Label(root, text=FIRST_RECORD_INSTRUCTION)
    instruction.pack(fill=tkinter.BOTH)

    logFile = open(LOG_FILE, 'w')

    for i in range(len(TARGET_WORDS) -15):
        parentFrame = ttk.Frame(root)
        parentFrame.pack(fill=tkinter.BOTH)
        makeFrame(parentFrame, SENTENCE_SAMPLES[i], TARGET_WORDS[i], NATIVE_SPEAKER_VOICE_SAMPLES[i], f"sentence{i}", logFile)
        parentFrame.grid_forget()
        parentFrame.destroy()
    
    logFile.close()

    instruction.forget()

# Create a single frame to record the phrase, listen to a native speaker's
# pronounciation, and then rerecord.
def makeFrame(parentFrame, sampleSentence, targetWord, exampleSpeechFile, soundFilePrefix, logFile):
    feedbackLabel = buildRecordAndListenBlock(parentFrame, sampleSentence, targetWord, exampleSpeechFile, soundFilePrefix + "rec1", logFile)

    soundFileNames = [soundFilePrefix + "rec2", soundFilePrefix + "rec3", soundFilePrefix + "rec4"]
    buildFinalRecordings(parentFrame, targetWord, soundFileNames, feedbackLabel, logFile)

    buildNextButton(parentFrame, (targetWord, soundFilePrefix))

# Provide button to record a phrase, and once recorded, provide button
# to listen to a native speaker's pronounciation.
def buildRecordAndListenBlock(parentFrame, sampleSentence, targetWord, exampleSpeechFile, soundFileName, logFile):
    wasPlayed = threading.Event()

    feedbackLabel = buildRecordBlock(parentFrame, wasPlayed, sampleSentence, targetWord, soundFileName, logFile)
    buildListenBlock(parentFrame, wasPlayed, exampleSpeechFile)
    return feedbackLabel

# Provide a button to record a phrase. First press begins recording,
# second ends recording, and subsequent presses play recording back.
def buildRecordBlock(grandParentFrame, wasPlayedUser, sampleSentence, targetWord, soundFileName, logFile):
    parentFrame = ttk.Frame(grandParentFrame, padding=(0,0,0,18))
    parentFrame.pack(fill=tkinter.BOTH)

    curFrame = ttk.Frame(parentFrame)
    curFrame.pack(fill=tkinter.BOTH)

    wasRecorded = threading.Event()

    currentPhrase = ttk.Label(curFrame, text=sampleSentence, font=('Verdana', 12, "italic"))
    currentPhrase.pack(side=tkinter.TOP, fill=tkinter.BOTH)

    feedBackFrame = ttk.Frame(parentFrame, padding=(0,18,0,0))
    feedBackFrame.pack(fill=tkinter.BOTH)

    feedbackLabel = ttk.Label(feedBackFrame)
    feedbackLabel.pack(side=tkinter.LEFT)

    buildRecordButton(curFrame, soundFileName, targetWord=targetWord, wasRecorded=wasRecorded, wasPlayed=wasPlayedUser, feedback=feedbackLabel, logFile=logFile)

    wasRecorded.wait()

    return feedbackLabel

# Create a button that plays a file on click.
def buildListenBlock(parentFrame, wasPlayedUser, fileName):
    curFrame = ttk.Frame(parentFrame, padding=(0,0,0,18))
    curFrame.pack(fill=tkinter.BOTH)

    wasPlayedNative = threading.Event()

    instruction = ttk.Label(curFrame, text=LISTEN_BACK_INSTRUCTION)
    instruction.pack(side=tkinter.TOP, fill=tkinter.BOTH)#grid(column=0, row=3, sticky=tkinter.W)

    button = ttk.Button(curFrame, text="Listen", command=lambda: threading.Thread(target=playFile, args=(fileName, label, wasPlayedNative)).start())
    button.pack(side=tkinter.LEFT)#grid(column=0, row=4, sticky=tkinter.W)

    label = ttk.Label(curFrame, text="0:00")
    label.pack(side=tkinter.LEFT)#grid(column=1, row=4, sticky=tkinter.W)

    # Ensure that user recording and native recording have both been played before
    while True:
        if (wasPlayedUser.is_set()):
            wasPlayedNative.wait()
            break
        elif (wasPlayedNative.is_set()):
            wasPlayedUser.wait()
            break
        time.sleep(0.001)

def playFile(fileName, label, wasPlayed):
    createRecording.CreateRecording.playFileAudio(fileName, label, wasPlayed=wasPlayed)

# Create three buttons to record voice samples. Each subsequent button is only
# available after the previous has been pressed. Once a recording is made,
# subsequent presses play the recording back.
def buildFinalRecordings(parentFrame, targetWord, soundFileNames, feedbackLabel, logFile):
    threeTriesFrame = ttk.Frame(parentFrame, padding=(0,0,0,18))
    threeTriesFrame.pack(fill=tkinter.BOTH)#grid(column=0, row=6, sticky=tkinter.W)

    instruction = ttk.Label(threeTriesFrame, text=FINAL_RECORD_INSTRUCTION, anchor='w')
    instruction.pack(fill=tkinter.BOTH)#grid(column=0, row=5, sticky=tkinter.W)

    buttons = []
    recordLabels = []

    for i in range(3):
        frame = ttk.Frame(threeTriesFrame)
        frame.pack(fill=tkinter.BOTH)

        buttons.append(ttk.Button(frame))
        buttons[i].pack(side=tkinter.LEFT)

        recordLabels.append(ttk.Label(frame))
        recordLabels[i].pack(side=tkinter.LEFT, fill=tkinter.BOTH)

    oneRecordingDone = threading.Event()

    createRecording.CreateRecording(buttons[0], recordLabels[0], soundFileNames[0], targetWord=targetWord, wasRecorded=oneRecordingDone, nextButton=buttons[1], feedback=feedbackLabel, logFile=logFile)
    createRecording.CreateRecording(buttons[1], recordLabels[1], soundFileNames[1], targetWord=targetWord, nextButton=buttons[2], feedback=feedbackLabel, logFile=logFile)
    createRecording.CreateRecording(buttons[2], recordLabels[2], soundFileNames[2], targetWord=targetWord, feedback=feedbackLabel, logFile=logFile)

    oneRecordingDone.wait()

# Build a button to exit this frame and build the next when pressed.
def buildNextButton(parentFrame, fileToDelete=None):
    endFrame = threading.Event()

    nextButton = ttk.Button(parentFrame, text="→", command=endFrame.set)
    nextButton.pack(side=tkinter.RIGHT)#grid(column=2, row=6, sticky=tkinter.W)

    endFrame.wait()

    if fileToDelete != None:
        finalRecordings = []
        finalRecordings.append(fileToDelete[0] + "-only" + fileToDelete[1] + "rec4.wav")
        finalRecordings.append(fileToDelete[1] + "rec4.wav")
        finalRecordings.append(fileToDelete[0] + "-only" + fileToDelete[1] + "rec3.wav")
        finalRecordings.append(fileToDelete[1] + "rec3.wav")
        finalRecordings.append(fileToDelete[0] + "-only" + fileToDelete[1] + "rec2.wav")
        finalRecordings.append(fileToDelete[1] + "rec2.wav")

        firstRecordingWordIsolated = fileToDelete[0] + "-only" + fileToDelete[1] + "rec1.wav"
        firstRecording = fileToDelete[1] + "rec1.wav"

        if os.path.exists(firstRecordingWordIsolated):
            os.remove(firstRecording)

        for i in range(len(finalRecordings)):
            if os.path.exists(finalRecordings[i]):
                for j in range(i+1, len(finalRecordings)):
                    try:
                        os.remove(finalRecordings[j])
                    except:
                        pass

# Build a button that records audio when first pressed,
# stops recording when pressed again, and then on subsequent
# presses plays back the audio.
def buildRecordButton(parentFrame, filename, targetWord=None, wasRecorded=None, wasPlayed=None, nextButton=None, logFile=None, feedback=None):
    button = ttk.Button(parentFrame)
    button.pack(side=tkinter.LEFT)

    label = ttk.Label(parentFrame)
    label.pack(side=tkinter.LEFT)

    createRecording.CreateRecording(button, label, filename, targetWord=targetWord, wasRecorded=wasRecorded, wasPlayed=wasPlayed, feedback=feedback, logFile=logFile)

# Build a zip file containing all the speaker audio recordings
# and the log file.
def buildZippedDataFile():
    # Compile all files to a single zip
    regex = re.compile('.*sentence.*\.wav$')

    # create a ZipFile object
    with zipfile.ZipFile(DATA_DIRECTORY + ".zip", 'w', compression=zipfile.ZIP_LZMA) as zipObj:
        # Iterate over all the files in directory
        for file in os.listdir("."):
            if regex.match(file):
                # Add file to zip
                zipObj.write(file)
                # Delete file
                try:
                    os.remove(file)
                except:
                    pass # unknown error

        # add log file
        zipObj.write(LOG_FILE)

def makeEndScreen(parentFrame):
    curFrame = ttk.Frame(parentFrame, padding=(0,0,0,18))
    curFrame.pack(fill=tkinter.BOTH)

    intro = ttk.Label(curFrame, text=END_SCREEN_INSTRUCTION, font=('Verdana', 12))
    intro.pack(side=tkinter.TOP, fill=tkinter.BOTH)

if __name__ == '__main__':
    main()