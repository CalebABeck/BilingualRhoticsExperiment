import tkinter
from tkinter import ttk
import pyaudio
import wave
import time
import threading
import isolateSound
import re

# TODO: Can't press playback button twice

AUDIO_FORMAT = pyaudio.paInt16
AUDIO_CHANNELS = 1
AUDIO_RATE = 44100
AUDIO_BUF_FRAMES = 1024

FOUND_CORRECT_TRILL = '''This sentence contains a trill (rolled R) sound. I detected this \
sound in your speech. Great work!'''
FOUND_CORRECT_TAP = '''This sentence contains an R 'tap' sound. I detected this sound in \
your speech. Great work!'''
FOUND_NEITHER_TRILL = '''This sentence contains two Rs in the middle of a word. Most native \
Spanish speakers pronounce this as a trill (rolled R), which I didn't find in your speech. \
This sound is unlike any in English, so \
most English speakers find this difficult to pronounce.\n\nIf you cannot make this sound, try \
first making an 'N' sound. Notice where your tongue is placed, as your tongue should be held \
in this same place to make the R sound. With your tongue held tensely in place, strongly \
and continuously exhale. With small adjustments to your tongue position, you may be able to \
make your tongue vibrate. Finally, activate your vocal cords (as you do when you hum or make a vowel \
sound) and you've made the correct sound.\n\n*Note that this trill sound is also typically used for any \
'R' at the start of a word, such as in "Roto".'''
FOUND_NEITHER_TAP = '''This sentence contains a single R in the middle of a word. Most native \
Spanish speakers pronounce this with a 'tap'. English speakers often make this same sound when \
pronouncing a 'T' or 'D' in the middle of a word. One example is the 'T' in 'city'. Try \
pronouncing the 'R' in this sentence with this sound.'''
FOUND_INCORRECT_TAP = '''I detected an 'R' tap in your pronounciation of this sentence which is \
how most native speakers would pronounce a single 'R' in the middle of a word in Spanish. Because \
this sentence includes a 'RR', most native speakers would pronounce this as a trill (rolled R).\
\n\nIf you cannot make this sound, try \
first making an 'N' sound. Notice where your tongue is placed, as your tongue should be held \
there as well to make this R sound. With your tongue held tensely in place, strongly \
exhale a long current of air. With small adjustments to your tongue position, you may be able to \
make your tongue vibrate. Finally, use your vocal cords to voice this sound (as you do when you hum or make a vowel sound) \
and you've made the correct sound. This sound is unlike any in English, and is often the most difficult \
for English speakers to learn. Don't worry if you can't make it. \n\n*Note that this R trill sound is also typically used for any \
'R' at the start of a word, such as in "Roto".'''
FOUND_INCORRECT_TRILL = '''I detected a trill (rolled R) in your pronounciation of this \
sentence, which is how most native speakers would pronounce an 'RR' in a word in Spanish. Because \
this sentence includes a single 'R', most native speakers would pronounce this as a tap. English \
speakers often make this same sound when pronouncing a 'T' or 'D' in the middle of a word. One \
example is the 'T' in 'city'. Try pronouncing the 'R' in this sentence with this sound.'''

class CreateRecording:
    def __init__(self, button, label, filename, targetWord=None, wasRecorded=None, wasPlayed=None, nextButton=None, logFile=None, feedback=None):
        self.filename = filename + ".wav" # Name of file to record speech to

        self.recording = True # True if in recording mode, false if in playback mode

        self.recordButtonUnpressed = True # True if button hasn't yet been pressed
        self.playButtonUnpressed = True # True if button has only been pressed 1 or 2 times

        self.wasRecorded = wasRecorded # An Event instance. Event will be set once recording is done.
        self.wasPlayed = wasPlayed # An Event instance. Event will be set once recording was played back at least once.
        self.nextButton = nextButton # Another button. It's state will be set to NORMAL once recording is done.

        self.targetWord = targetWord # Word to analyze for tap, trill, or approximant

        self.lock = threading.Event() # Set once recording is done

        self.logger = logFile # Records Praat Measurements

        self.button = button
        self.button.configure(text="Record", command=self.buttonRecordMode)

        self.label = label
        self.label.configure(text="0:00")

        self.feedbackLabel = feedback

    # This method is called on the first two button presses. The first
    # begins recording. The second ends and saves the recording, then
    # changes the button to call playaudio when pressed.
    def buttonRecordMode(self):
        if (self.recordButtonUnpressed):
            self.recordButtonUnpressed = False
            threading.Thread(target=self.record).start()
        else:
            self.recording = False
            threading.Thread(target=self.buttonPlaybackMode).start()

    # This method is called on all button presses past the first two.
    # Play back the audio recorded by the first presses.
    def buttonPlaybackMode(self):
        if (self.playButtonUnpressed):
            self.playButtonUnpressed = False
            self.lock.wait()
            self.button.config(text="Play Back")
        else:
            threading.Thread(target=CreateRecording.playFileAudio, args=(self.filename, self.label, self.wasPlayed)).start()

    # Ran in a thread when program is called to begin a recording. Records
    # audio until recording is set to False. Then saves the recording
    # to a .wav file labeled recording[number].wav in the current directory.
    def record(self):
        self.lock.clear()
        audio = pyaudio.PyAudio()
        stream = audio.open(format=AUDIO_FORMAT,
                            channels=AUDIO_CHANNELS,
                            rate=AUDIO_RATE,
                            input=True,
                            frames_per_buffer=AUDIO_BUF_FRAMES)

        frames = []

        start = time.time()
        prevSecs = -1

        while self.recording:
            frames.append(stream.read(AUDIO_BUF_FRAMES))

            # Update time label for button to indicate current time in the recoring
            prevSecs = CreateRecording.updateTimeLabel(self.label, start, prevSecs)

        stream.stop_stream()
        stream.close()
        audio.terminate()

        with wave.open(self.filename, "wb") as writeFile:
            writeFile.setnchannels(AUDIO_CHANNELS)
            writeFile.setsampwidth(audio.get_sample_size(AUDIO_FORMAT))
            writeFile.setframerate(AUDIO_RATE)
            writeFile.writeframes(b"".join(frames))

        self.lock.set()

        if (isinstance(self.wasRecorded, threading.Event)):
            self.wasRecorded.set()

        if (isinstance(self.nextButton, ttk.Button)):
            self.nextButton.config(state=tkinter.NORMAL)
        
        if self.targetWord != None and self.feedbackLabel != None:
                soundFound = isolateSound.findAndAnalyze(self.filename, self.targetWord, self.logger)
                matchTrill = re.search("rr", self.targetWord)
                matchTap = re.search("r", self.targetWord)

                if soundFound == isolateSound.TRILL:
                    if matchTrill != None:
                        self.feedbackLabel.config(text=FOUND_CORRECT_TRILL)
                    else:
                        self.feedbackLabel.config(text=FOUND_INCORRECT_TRILL)
                elif soundFound == isolateSound.TAP:
                    if matchTap != None and matchTrill == None:
                        self.feedbackLabel.config(text=FOUND_CORRECT_TAP)
                    else:
                        self.feedbackLabel.config(text=FOUND_INCORRECT_TAP)
                else:
                    if matchTrill != None:
                        self.feedbackLabel.config(text=FOUND_NEITHER_TRILL)
                    else:
                        self.feedbackLabel.config(text=FOUND_NEITHER_TAP)
    
    def isRecorded(self):
        return self.wasRecorded

    def isPlayed(self):
        return self.wasPlayed

    # Play the audio from filename
    def playFileAudio(filename, label, wasPlayed=None):
        with wave.open(filename, 'rb') as readFile:
            audio = pyaudio.PyAudio()

            # 'output = True' indicates that the sound will be played rather than recorded
            stream = audio.open(format=AUDIO_FORMAT,
                                channels=AUDIO_CHANNELS,
                                rate=AUDIO_RATE,
                                output=True)

            data = readFile.readframes(AUDIO_BUF_FRAMES)

            start = time.time()
            prevSecs = -1

            # Play the sound by writing the audio data to the stream and display the time
            while data != b'':
                stream.write(data)
                data = readFile.readframes(AUDIO_BUF_FRAMES)

                prevSecs = CreateRecording.updateTimeLabel(label, start, prevSecs)

            stream.close()
            audio.terminate()

            if (isinstance(wasPlayed, threading.Event)):
                wasPlayed.set()

    def updateTimeLabel(label, start, prevSecs):
        timePassed = time.time() - start
        secs = int(timePassed % 60)
        mins = int(timePassed // 60)
        if (secs != prevSecs):
            label.configure(text=f"{mins}:{secs:02d}")
        
        return secs