from ast import Try
from concurrent.futures.thread import _WorkItem
from math import e

import pytube
import requests
from spleeter.separator import Separator
from spleeter.audio.adapter import AudioAdapter
import shutil
import subprocess
import json
import os
import datetime
import sys
import argparse
import librosa
import numpy as np

global separator
separator = None


def FormatTime(tm):
    st = "00:"    
    if tm.minute < 10:
        st += "0"
    st += str(tm.minute)
    st += ":"
    if tm.second < 10:
        st += "0"
    st += str(tm.second)
    
    st += "." + str(tm.microsecond).zfill(2)
   
    return st

def GetAssLyricOffset(st):
    lines = st.split("\n")
    indx = -1
    times = []
    realoffset = None
    
    l = lines[11]
    timestart = l[12:12+11]     
    print("Start Time: " + str(timestart))
    minu = int(timestart[0:2])
    sec = int(timestart[3:5])
    mic = int(timestart[6:8])
        
    st = (minu*60) + sec + (mic/100)    
    
    return st
    

def GetLyricOffset(st):
    lines = st.split("\n")
    indx = -1
    times = []
    realoffset = None
    
    l = lines[0]
    timestart = l[1:9]        
    minu = int(timestart[0:2])
    sec = int(timestart[3:5])
    mic = int(timestart[6:8])
        
    st = (minu*60) + sec + (mic/100)
    
    l = lines[len(lines)-1]
    if l == "":
        l = lines[len(lines)-2]
    timestart = l[1:9]        
    minu = int(timestart[0:2])
    sec = int(timestart[3:5])
    mic = int(timestart[6:8])
        
    en = (minu*60) + sec + (mic/100)
    
    return (st,en)

def WriteLyricFile(st,offset = 0):
    fl = open("ytvideo.ass",'w',encoding='utf-8')
    fl.write("[Script Info]\n")
    fl.write("ScriptType: v4.00+\n")
    fl.write("PlayResX: 384\n")
    fl.write("PlayResY: 288\n")
    fl.write("\n")
    fl.write("[V4+ Styles]\n")
    fl.write("Format: Name, Fontname, Fontsize, PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n")
    fl.write("Default,Helvetica,16,&HFF00,&Hffffff,&H0,&H0,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,0\n")
    fl.write("\n")
    fl.write("[Events]\n")
    fl.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = st.split("\n")
    indx = -1
    times = []
    realoffset = None
    microtweak = None
    
    for l in lines:
        #Parse Starting Time
        timestart = l[1:9]
        #print(str(timestart))
        minu = int(timestart[0:2])
        sec = int(timestart[3:5])
        mic = int(timestart[6:8])
        
        if realoffset is None:
            if offset is not None:
                print("First Lyric File Offset: " + str(((minu*60) + sec + (mic/100))))
                print("Video First Lyric Offset: " + str(offset))            
                realoffset = offset - ((minu*60) + sec + (mic/100))
                print("Video Timing Adjustment: " + str(realoffset))
                microtweak = (realoffset % 1)*100
                if realoffset < 0:
                    if microtweak > 0:
                        microtweak = -(100-microtweak)
            else:
                realoffset = 0
                microtweak = 0
                    
        #print("Adding " + str(realoffset) + " seconds to " + str(minu) + ":" + str(sec) + ":" + str(mic) + " (" + str(microtweak) + ")")        
        mic += microtweak        
            
        sec += int(realoffset)        
        if mic > 99:
            sec += 1
            mic -= 100
        if mic < 0:
            mic += 100
            sec -= 1
        if sec > 59:
            minu += 1
            sec -= 60
        if sec < 0:
            sec += 59;
            minu -= 1;
            if minu < 0:
                minu = 0
                sec = 0
        #print("   Result = " + str(minu) + ":" + str(sec) + ":" + str(mic))
        tm = datetime.time(0,int(minu),int(sec),int(mic))
        times.append(tm)
        
    #print(str(times))
        
    indx = -1
    for l in lines:
        indx+=1
        timestart = FormatTime(times[indx])
        try:
            timeend = times[indx+1]
        except:
            timeend = times[indx]        
            
        timeend = FormatTime(timeend)
        #print(str(timestart))
        #print(str(timeend))
            
        content = l[10:].strip()
        fl.write("Dialogue: 0," + timestart + "," + timeend + ",Default, NTP,0,0,0,," + content + "\n")
    fl.flush()
    fl.close()

def common_substrings(str1,str2,min_com):
    len1,len2=len(str1),len(str2)

    if len1 > len2:
        str1,str2=str2,str1 
        len1,len2=len2,len1
    #short string=str1 and long string=str2

    #min_com = int(input('Please enter the minumum common substring length:'))
    
    cs_array=[]
    for i in range(len1,min_com-1,-1):
        for k in range(len1-i+1):
            if (str1[k:i+k] in str2):
                flag=1
                for m in range(len(cs_array)):
                    if str1[k:i+k] in cs_array[m]:
                    #print(str1[k:i+k])
                        flag=0
                        break
                if flag==1:
                    cs_array.append(str1[k:i+k])
    if len(cs_array):
        #print(cs_array)
        return cs_array
    else:
        #print('There is no any common substring according to the parametres given')    
        return None

def Kareokise(songname,artist,adjust=None,statusfunction = None):
    bestresult = None

    if statusfunction is not None:
        statusfunction("Searching")    
    
    reloadData = True
    if adjust != None:
        reloadData = False
        if adjust == "dynamic":
            adjust = None
            
    bestresult = FindYTSong(songname,artist)
        
    if bestresult is None:
        statusfunction("Failed")
        return
    
    print("Found: " + bestresult.title)
    finaltitle = bestresult.title
    finallength = bestresult.length
    
    if reloadData == True:
        print("Downloading Thumbnail: " + bestresult.thumbnail_url)
        thumb = requests.get(bestresult.thumbnail_url,stream=True)
        ls = open('thumbnail.jpg','wb')
        shutil.copyfileobj(thumb.raw,ls)
        ls.flush()
        ls.close()
        
    
    print("Downloading YouTube Video")
    if statusfunction is not None:
        statusfunction("Downloading")

    if reloadData == True:                
        bestresult.streams.filter(progressive=True,file_extension='mp4').order_by('resolution').desc().first().download(filename="ytvideo.mp4")
    
    if reloadData == True:
        try:
            os.remove("ytaudio.mp3")    
        except:
            pass

        print("Extracting Audio File")
        subprocess.call(["ffmpeg","-i","ytvideo.mp4","-map","0:a","-acodec","libmp3lame","ytaudio.mp3"])

    print("Splitting...")
    if statusfunction is not None:
        statusfunction("Extracting")
        
    global separator
    if separator is None:
        separator = Separator('spleeter:2stems', multiprocess=False)
    audio_loader = AudioAdapter.default()
    sample_rate = 44100    
    
    if reloadData == True:
        try:
            os.remove("ytaudio/accompaniment.wav")    
        except:
            pass
        try:
            os.remove("ytaudio/vocals.wav")    
        except:
            pass

        ## Perform the separation :

        if statusfunction is not None:
            statusfunction("Splitting")            
    
        basefolder = os.path.dirname(__file__)

        try:
            prediction = separator.separate_to_file(basefolder + '/ytaudio.mp3',basefolder)
        except:
            if statusfunction is not None:
                statusfunction("Failed")            
            return

    #if lyrics != "":
    #    print(lyrics)
        
    #Transcribe lyrics
    print("Loading Audio")
    if statusfunction is not None:
        statusfunction("Analysing")
    
    x,sr = librosa.load('ytaudio/vocals.wav')
    N_fft = 2048
    
    print("Normalising...")
    S = librosa.stft(x,n_fft=int(N_fft),hop_length=int(N_fft/2))
    D = librosa.amplitude_to_db(np.abs(S),ref = np.max)
    print("Max DB: " + str(np.max(abs(D))))    

    possiblestart = []
    
    print("Finding Silence...")
    splits = librosa.effects.split(x,top_db = np.max(abs(D))/2)
    if len(splits) > 0:
        #for s in splits:
            #ln = (s[1] - s[0])/sr
            #if ln >= 1:
            #    possiblestart.append(s[0] / sr)
        trxoffset = splits[0][0] / sr
        print("First Vocal Offset: " + str(trxoffset) + " seconds")    
        lst = len(splits)-1
        trxmax = splits[lst][1] / sr
        possiblestart.append(trxoffset)

        print("Total Vocal Time: " + str(trxmax - trxoffset))
    
    #Look for first significant DB spike...
    firstbump = trxoffset
    indx = int(trxoffset * sr)
    threshold = np.max(abs(x))*0.314
    #print(str(x.shape))
    samplelen = int(x.shape[0])    
    for r in range(indx,samplelen):
        mx = np.max(x[r])
        if x[r] > threshold:
            firstbump = r / sr
            print("Possible vocal spike @ " + str(firstbump) + " (threshold: " + str(threshold) + ")")
            samples = abs(x[r:r+int(sr*0.5)])
            avg = sum(samples) / (sr*0.5)
            print("Average over next half-second..." + str(avg))
            if avg > 0.006:
                print("First major vocal spike @ " + str(firstbump))
                possiblestart.append(firstbump)
                break
            else:
                print("Ignoring spike - believed to be a pop or other artifact.")
        
    del x
    del S
    del D    
    
    print("Searching for Lyrics")    
    if statusfunction is not None:
        statusfunction("Get Lyrics")

    lyricmatch = None
    if 'lyric' not in finaltitle.lower():
        if reloadData == False:
            fl = open('lyrics.json','r',encoding='utf-8')
            content = fl.read()
            #print(str(content))
            items = json.loads(content)
            fl.close()
        else:
            res = requests.get("https://lrclib.net/api/search?track_name=" + songname + "&artist_name=" + artist)
            items = json.loads(res.text)
            fl = open("lyrics.json",'w',encoding='utf-8')
            fl.write(res.text)
            fl.flush()
            fl.close()
        
        if len(items) == 0:            
            res = requests.get("https://lrclib.net/api/search?track_name=" + songname)
            items = json.loads(res.text)            
            
        candidates = []
        for i in items:
            if i['trackName'].upper().strip().find(songname.upper().strip()) == 0:
                candidates.append(i)
                
        if len(candidates) == 0:
            candidates = items
            
        finalcandidates = []
        for i in candidates:
            if i['artistName'].upper().strip().find(artist.upper().strip()) == 0:
                finalcandidates.append(i)        
        
        if len(finalcandidates) == 0:
            finalcandidates = candidates
            
        mxmx = 0
        starttime = possiblestart[len(possiblestart)-1]
        beststart = None
        bestsize = None
        backupmatch = None
        lyricmatch = None
        tweak = 0
        for v in finalcandidates:        
            subs = common_substrings((v['trackName'] + " " + v['artistName']).upper(),finaltitle.upper(),5)
            if 'REMIX' in v['trackName'].upper():
                continue
            if 'INSTRUMENTAL' in v['trackName'].upper():
                continue
            if ' LIVE' in v['trackName'].upper().replace("(",""):
                continue
            if ' LIVE' in v['albumName'].upper().replace("(",""):
                continue
            if ' MIX' in v['trackName'].upper().replace("(",""):
                continue
            if ' REMIX' in v['trackName'].upper().replace("(",""):
                continue
            if ' ACAPELLA' in v['trackName'].upper().replace("(",""):
                continue            
            if 'A CAPELLA' in v['trackName'].upper().replace("(",""):
                continue            
            if artist != "":
                if 'artistName' in v:
                    if v['artistName'].upper().find(artist.upper()) == -1:
                        print("No Artist Given")
                        continue
            print(v['trackName'] + " / " + v['artistName'])                       
                
            if subs is not None:
                mx = 0        
                for r in subs:
                    mx += len(subs)
                
                if v['syncedLyrics'] is not None:
                    startoffset,endoffset = GetLyricOffset(v['syncedLyrics'])
                    for tripping in possiblestart:
                        drift = abs(startoffset - tripping) + tweak                        
                        print("Comparing Offset " + str(startoffset) + " vs " + str(tripping))
                        if beststart is None:
                            beststart = drift
                            lyricmatch = v
                            starttime = tripping
                            print("New Best Fit: " + str(beststart) + " / " + str(startoffset))
                            if drift < 0.1:
                                break
                        if drift < beststart:
                            starttime = tripping
                            beststart = drift
                            lyricmatch = v
                            print("New Best Fit: " + str(beststart) + " / " + str(startoffset))
                            if drift < 0.1:
                                break
                    if beststart < 0.1:
                        break
                    
            tweak += 0.2                            
                
                #diff = finallength - v['duration']
                #print("Checking " + v['trackName'] + " " + v['artistName'] + " @ " + str(v['duration']) + " / " + str(finallength))       
                ##if v['trackName'].find("(") != -1:
                ##    continue
                #if bestsize is None:
                #    if 'syncedLyrics' in v:
                #        if v['syncedLyrics'] is not None:
                #            lyricmatch = v
                #            beststart = drift
                #            bestsize = abs(v['duration'] - finallength)
                #            print("Found " + v['trackName'] + " " + v['artistName'])
                #else:
                #    if 'syncedLyrics' in v:
                #        if v['syncedLyrics'] is not None:
                #            if abs(v['duration'] - finallength) < bestsize or offdiff < beststart:
                #                print("Better Option: (" + str(v['duration'] - finallength) + " vs " + str(bestsize) + ")" + v['trackName'] + " " + v['artistName'])
                #                lyricmatch = v
                #                bestsize = abs(v['duration'] - finallength)                    
                #                beststart = offdiff
    #sys.exit()     
    lyrics = ""
    print("Matching Lyrics:")
    if lyricmatch is not None:
        if 'syncedLyrics' in lyricmatch:
            lyrics = lyricmatch['syncedLyrics']
        else:
            lyrics = lyricmatch['plainLyrics']
            
        #print(str(lyricmatch))
    else:
        print("No Lyric Data Found")
    #print("Lyrics: " + lyrics)

    trxoffset = starttime - 0.5
    
    #OK - now we decide who to trust.
    if lyrics != "":
        startoffset,endoffset = GetLyricOffset(lyrics)
    
        #if firstbump > startoffset and startoffset > trxoffset:
        #    trxoffset = firstbump
        #    print("Overriding silence detector with vocal spike detector")
        

        print("Total Lyric Time: " + str(startoffset) + " to " + str(endoffset) + ": " + str(endoffset - startoffset))
        print("Video Duration: " + str(bestresult.length))
        print("Lyric Duration: " + str(lyricmatch['duration']))
        if adjust is not None:
            if adjust == "default":
                adjust = startoffset        
            
            
        trustedoffset = 0
        if adjust is not None:
            #The user has forced an adjustment setting
            if adjust == "auto":
                trustedoffset = trxoffset
            else:
                if adjust == "default":
                    trustedoffset = None
                else:
                    trustedoffset = adjust        
        else:
            #Compare different durations.
            textdur = lyricmatch['duration']
            videodur = bestresult.length   
            #videodur = trxmax - trxoffset
            off = videodur - textdur
            print("Comparing Lyric Length Of " + str(textdur) + " against video of " + str(videodur) + " = Start Offset " + str(startoffset))
            if off == 0:
                print("Perfect Sync");
                if abs(startoffset - trxoffset) > 1:
                    print("But starting times differ significantly. Use analysed start time...")
                    trustedoffset = trxoffset
                else:
                    print("Using given lyric offset")
                    trustedoffset = startoffset
            else:
                if beststart < 0.05:
                    print("Excellent lyric match - using lyric timing regardless of other factors.")
                    trustedoffset = startoffset
                else:
                    if startoffset > 5 and trxoffset < 2:
                        #Long expected gap + no actual gap - possible bad audio match. Assume lyrics are right.
                        print("Think audio analysis might be wrong. Use lyric timing.")
                        trustedoffset = startoffset
                    else:
                        if off > 0 and off < 3.5:    
                            #If there are only small differences and the LYRIC offset is greater than the detected start of vocals, use the lyric offset.
                            if startoffset > trxoffset:
                                #We can probably trust the sequencing as-is
                                print("Going with original lyric timing...")
                                trustedoffset = startoffset
                            else:
                                #Use the detected lyric start position
                                trustedoffset = trxoffset - 0.5
                        else:
                            print("Size Difference = " + str(off) + " / " + str(startoffset - max(possiblestart)))
                            if off > 8 or abs(startoffset - max(possiblestart)) > 8:
                                print("Difference between audio and lyric start is large - using largest analysed offset")
                                trxoffset = max(possiblestart)
                            print("Going with analysed lyric start position (" + str(trxoffset) + ")")
                            trustedoffset = trxoffset - 0.5                        
    else:
        trustedoffset = 0
    
    workingtitle = bestresult.title
    workingtitle = workingtitle.replace('"','')
    workingtitle = workingtitle.replace(':','')
    workingtitle = workingtitle.replace('\\','')
    workingtitle = workingtitle.replace('/','')
    indx = workingtitle.find('(')
    if indx != -1:
        workingtitle = workingtitle[0:indx-1].strip()
    indx = workingtitle.find('[')
    if indx != -1:
        workingtitle = workingtitle[0:indx-1].strip()

    try:
        os.remove(workingtitle + ".mp4")    
    except:
        pass    
    
    print("Reintegrating...")
    if statusfunction is not None:
        statusfunction("Creating Video")
    if lyrics != "":        
        off = trustedoffset                
                
        print("Lyric Offset: " + str(off))
                    
        WriteLyricFile(lyrics,float(off))        

        #sys.exit()
        #subprocess.call(["ffmpeg","-i","ytvideo.mp4","-i","ytaudio/accompaniment.wav","-map","0:v:0","-map","1:a:0","-vf","ass=ytvideo.ass",workingtitle + ".mp4"])
        subprocess.call(["ffmpeg","-i","ytvideo.mp4","-i","ytaudio/accompaniment.wav","-c:v","copy","-map","0:v:0","-map","1:a:0",workingtitle + ".mp4"])
    else:
        print("No Lyrics Found!")
        subprocess.call(["ffmpeg","-i","ytvideo.mp4","-i","ytaudio/accompaniment.wav","-c:v","copy","-map","0:v:0","-map","1:a:0",workingtitle + ".mp4"])
        
    subprocess.call(["ffmpeg","-i","ytaudio/vocals.wav","-map","0:a","-acodec","libvorbis",workingtitle + ".ogg"])
        
    return workingtitle + ".mp4"

def FindYTSong(songname,artist):
    results = pytube.Search(artist + " - " + songname)
    
    bestscore = None        
    best = None
    #First, search for both artist and song...    

    penalties = {}
    penalties["OFFICAL AUDIO"] = 25
    penalties[" AUDIO"] = 20
    penalties[" LIVE"] = 40
    penalties[" LYRIC"] = 10
    penalties[" KARAOKE"] = 10
    penalties["WOODSTOCK"] = 10
    penalties["ALTERNATE"] = 10
    
    bonuses = {}
    bonuses[" OFFICIAL"] = 10
    bonuses[" HD"] = 10
    bonuses[" 4K"] = 10
            
    indx = -1
    for n in results.results:            
        indx += 1
        
        score = 0
        
        if artist != "":                
            try:                
                if artist.upper() in n.title.upper():
                    score += 50       
            except:
                pass
        
        try:                 
            if songname.upper() in n.title.upper():                
                score += 50                
        except:
            pass
        
        working = n.title.upper().replace("("," ").replace("["," ")
        
        for k in penalties:
            
            if songname in working:
                score -= penalties[k]

        for k in bonuses:
            
            if songname in working:
                score += bonuses[k]
   
        if score > 45:
            print(n.title + " has a score of " + str(score))
            if bestscore is None or score > bestscore:
                best = n
                bestscore = score
    
    return best

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
                prog='Karaoke',
                description='Creates a Karaoke Video')

    parser.add_argument('song')           # positional argument
    parser.add_argument('artist',default="")           # positional argument
    parser.add_argument('-a', '--adjust',action='store',default=None)  # on/off flag

    args = parser.parse_args()

    songname = args.song#"All About That Bass"
    artist = args.artist#"Trainor"

    Kareokise(songname,artist,adjust = args.adjust)