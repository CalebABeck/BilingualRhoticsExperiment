import wave
import sys
import json
from math import trunc
import parselmouth

import vosk

TRILL = 'trill'
TAP = 'tap'
OTHER = 'other'

AUDIO_CHANNELS = 1
AUDIO_RATE = 44100
AUDIO_BUF_FRAMES = 1024

def isolateWord(filename, targetWord, logger=None):
    if logger != None:
        logger.write("\t" + targetWord + "\n")

    vosk.SetLogLevel(-1) # Disable debug messages

    wf = wave.open(filename, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print("Audio file must be WAV format mono PCM.")
        sys.exit(1)

    model = vosk.Model(model_path="vosk-model-small-es-0.42")

    rec = vosk.KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    data = wf.readframes(4000)

    while len(data) != 0:
        rec.AcceptWaveform(data)
        data = wf.readframes(4000)

    resultDict = json.loads(rec.FinalResult())

    detectedWord = "ArbitraryIncorrectValue"

    for i in resultDict["result"]:
        if i["word"].lower() == targetWord.lower():
            detectedWord = i["word"].lower()
            if logger != None:
                logger.write("found word\n")
            break
    
    # If didn't find a match for the word, see if there's a close match
    if i["word"].lower() != targetWord.lower():
        detectedWord = findCloseMatch(resultDict, targetWord.lower(), logger)

        # If word is not found, return None
        if detectedWord == None:
            if logger != None:
                logger.write("no match\n")
            return None
        else: # Otherwise, proceed with the close match word
            i = detectedWord

    # file to extract the snippet from
    with wave.open(filename, "rb") as infile:
        # get file data
        sampwidth = infile.getsampwidth()
        # set position in wave to start of segment
        infile.setpos(int(i["start"] * AUDIO_RATE))
        # extract data
        data = infile.readframes(int((i["end"] - i["start"]) * AUDIO_RATE))

    newFile = targetWord + "-only" + filename

    # write the extracted data to a new file
    with wave.open(newFile, 'w') as outfile:
        outfile.setnchannels(AUDIO_CHANNELS)
        outfile.setsampwidth(sampwidth)
        outfile.setframerate(AUDIO_RATE)
        outfile.setnframes(int(len(data) / sampwidth))
        outfile.writeframes(data)

    return newFile

# Determine if any results in resultDict are a close match to
# targetWord. Return targetWord if so.
# A close match is defined as a word that is the same but with
# one letter being different, one letter being added, or one
# letter being removed.
def findCloseMatch(resultDict, targetWord, logger):
    for i in resultDict["result"]:
        detectedWord = i["word"].lower()
        
        # 1 letter wrong
        closeMatch = True
        if len(detectedWord) == len(targetWord):
            lettersOff = 0
            j = 0
            while j < len(targetWord):
                if detectedWord[j] != targetWord[j]:
                    lettersOff += 1
                    if lettersOff > 1:
                        closeMatch = False
                        break
                j += 1
            
            if closeMatch:
                if logger != None:
                    logger.write("using: " + detectedWord + "\n")
                return i

        # 1 letter added
        closeMatch = True
        if len(detectedWord) - 1 == len(targetWord):
            lettersOff = 0
            j = 0
            k = 0
            while k < len(targetWord):
                if detectedWord[j] != targetWord[k]:
                    lettersOff += 1
                    j += 1
                    if lettersOff > 1 or detectedWord[j] != targetWord[k]:
                        closeMatch = False
                        break
                j += 1
                k += 1
            
            if closeMatch:
                if logger != None:
                    logger.write("using: " + detectedWord + "\n")
                return i

        # 1 letter missing
        closeMatch = True
        if len(detectedWord) == len(targetWord) - 1:
            lettersOff = 0
            j = 0
            k = 0
            while j < len(detectedWord):
                if detectedWord[j] != targetWord[k]:
                    lettersOff += 1
                    k += 1
                    if lettersOff > 1 or detectedWord[j] != targetWord[k]:
                        closeMatch = False
                        break
                j += 1
                k += 1
            
            if closeMatch:
                if logger != None:
                    logger.write("using: " + detectedWord + "\n")
                return i
    
    # Loop ended without returning, meaning no match found
    return None

def analyzeWord(filename, logger=None):
    sound = parselmouth.Sound(filename)

    with wave.open(filename, 'rb') as file:
        duration = file.getnframes() / AUDIO_RATE

    spectralPowerList = getSpectralPowerList(sound, duration)

    # Omit initial and end silence to get better average
    # This will help calibrate occlusion threshhold
    spectralPowerList = trimSpectralPowerList(spectralPowerList)

    # spectralPowerList average
    average = sum([row[0] for row in spectralPowerList]) / len(spectralPowerList)

    durationList = []
    intensity = sound.to_intensity(time_step=0.0005)
    times = intensity.xs()
    intensities = intensity.values.T
    for i in range(len(times)):
        durationList.append((intensities[i][0], times[i]))
    
    minima = findAllLocalMinima(durationList)

    trillFound = checkForTrill(minima, spectralPowerList, logger)
    if trillFound == TRILL:
        return TRILL

    pitch = sound.to_pitch()
    pulses = parselmouth.praat.call([sound, pitch], "To PointProcess (cc)")
    numPulses = parselmouth.praat.call(pulses, "Get number of points")
    pulseList = []
    for pulseIndex in range(1, numPulses+1):
        pulseList.append(parselmouth.praat.call(pulses, "Get time from index", pulseIndex))

    # Check for tap
    tapsFound = 0
    i = 0
    j = 0
    numFalseOutliers = 0
    min = None
    tapStart = None
    tapEnd = None
    while i < len(spectralPowerList):
        if spectralPowerList[i][0] < (average / 2.5):
            sharpOutlier = False
            outliers = 0
            j = 0
            while i < len(spectralPowerList) and j < 25 and outliers < 6:
                if spectralPowerList[i][0] > (average / 2.5) and spectralPowerList[i][0] < (average / 1.3):
                    outliers += 1
                elif spectralPowerList[i][0] > (average / 1.3):
                    if sharpOutlier:
                        break
                    sharpOutlier = True
                i += 1
                j += 1
            
            # Do not count 'outliers' that came at the occlusion. Outliers are
            # only sound in the middle of the occlusion
            numFalseOutliers = 0
            for k in range(outliers):
                if spectralPowerList[i-1-k][0] < (average / 2.5):
                    j -= 1
                    numFalseOutliers += 1

            if j <= 30 and j >= 8:
                numPulsesInRange = 0
                for k in pulseList:
                    if k > spectralPowerList[i-j-numFalseOutliers][1] and k < spectralPowerList[i-numFalseOutliers][1]:
                        numPulsesInRange += 1
                
                if numPulsesInRange >= j//10:
                    for min in minima:
                        if min[1] < spectralPowerList[i-numFalseOutliers][1] and min[1] > spectralPowerList[i-j-numFalseOutliers][1]:
                            tapStart = spectralPowerList[i-j-numFalseOutliers][1]
                            tapEnd = spectralPowerList[i-numFalseOutliers][1]
                            tapsFound += 1
                            break
        i += 1

    if tapsFound == 1:
        if logger != None:
            logger.write("tap found\n")
            logger.write(f"occlusion minima: {min}\n")
            logger.write(f"occlusion length: {j*0.002}\n")
            logger.write(f"occlusion midpoint: {(tapStart + tapEnd) / 2}\n")
        return TAP
    else:
        if logger != None:
            logger.write("no tap or trill found \n")
        return OTHER

def getSpectralPowerList(sound, duration):
    spectralPowerList = []
    spectrogram = sound.to_spectrogram()

    i = 0
    while i < duration:
        power = spectrogram.to_spectrum_slice(i).get_band_energy()
        spectralPowerList.append((power, i))
        
        i += 0.002
    
    return spectralPowerList

def trimSpectralPowerList(spectralPowerList):
    # Omit initial silence
    for i, cur in enumerate(spectralPowerList):
        if cur[0] > 20:
            break
    trimmedList = spectralPowerList[i:]

    # Now omit end silence
    for i in range(len(trimmedList)-1, 0, -1):
        if trimmedList[i][0] > 20:
            break
    trimmedList = trimmedList[:i]

    return trimmedList

def findAllLocalMinima(durationList):
    minima = []
    
    for i in range(16, len(durationList) - 16):
        if durationList[i][0] < durationList[i-1][0] and durationList[i][0] < durationList[i+1][0]:
            if ((((durationList[i - 20][0] - durationList[i][0]) + (durationList[i + 20][0] - durationList[i][0])) / 2) > 0.6
                and durationList[i - 8][0] > durationList[i][0] and durationList[i + 8][0] > durationList[i][0]):
                #smoothedMin = True
                #for j in range(2, 10):
                #    if not (durationList[i][0] < durationList[i-j][0] and durationList[i][0] < durationList[i+j][0]):
                #        smoothedMin = False
                #        break
                #if smoothedMin:
                    minima.append(durationList[i])
    
    return minima

def checkForTrill(minima, spectralPowerList, logger):
    for i in range(len(minima) - 1):
        if minima[i+1][1] - minima[i][1] < .06:
            indexIntoSpectralList1 = trunc((minima[i][1] - spectralPowerList[0][1]) / 0.002)
            spectralPowerTally1 = 0
            for j in range(5):
                spectralPowerTally1 += spectralPowerList[indexIntoSpectralList1 - 2 + j][0]
            spectralPowerTally1 /= 5

            indexIntoSpectralList2 = trunc((minima[i+1][1] - spectralPowerList[0][1]) / 0.002)
            spectralPowerTally2 = 0
            for j in range(5):
                spectralPowerTally2 += spectralPowerList[indexIntoSpectralList2 - 2 + j][0]
            spectralPowerTally2 /= 5

            indexIntoSpectralList3 = (indexIntoSpectralList1 + indexIntoSpectralList2) // 2
            spectralPowerTally3 = 0
            for j in range(5):
                spectralPowerTally3 += spectralPowerList[indexIntoSpectralList3 - 2 + j][0]
            spectralPowerTally3 /= 5

            if ((spectralPowerTally1 + spectralPowerTally2) / 2) < (spectralPowerTally3 / 2):
                if logger != None:
                    logger.write("trill found\n")
                    logger.write(f"first occlusions: {minima[i][1]}, {minima[i+1][1]}" + "\n")
                return TRILL
    
    return None

def findAndAnalyze(filename, target, logger=None):
    try:
        newFile = isolateWord(filename, target, logger)
        if newFile != None:
            return analyzeWord(newFile, logger)
        else:
            if logger != None:
                logger.write("no tap or trill found\n")
            return OTHER
    except:
        if logger != None:
            logger.write("no tap or trill found\n")
        return OTHER

#analyzeWord("isolatedtest1.wav")