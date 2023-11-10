from pickle import PUT
from flask import Flask, redirect,url_for,session,make_response
from flask import request
import threading
import shutil
import glob
import os
import pytube
import json
import datetime
import time
import traceback

app = Flask(__name__,static_url_path='',static_folder='web')

import karaoke

jobid = 1
queue = []
conversions = []
songs = []

global reftime
reftime = datetime.datetime.now()

def mainPage():
    fl = open('index.html','r')
    rd = fl.read();
    fl.close();
      

    rd = rd.replace("[QUEUE]",GetQueueList())    
        
    rd = rd.replace("[SONGS]",GetSongList())
    
    return rd

def CheckForNextJob():
    nextwaiting = None
    busy = False
    for n in conversions:
        if n.progress == "In Queue":
            if nextwaiting is None:
                nextwaiting = n
        if n.progress != "In Queue" and n.progress != "Complete" and n.progress != "Failed":
            busy = True
            break
                
    if busy == False:
        print("Starting Conversion...")
        if nextwaiting != None:
            nextwaiting.Start()

class ConversionJob:
    def __init__(self):
        self.id = None
        self.artist = ""
        self.title = ""
        self.progress = "In Queue"
        self.thread = None
        self.finalfile = ""
        
    def UpdateProgress(self,st):
        self.progress = st
        
    def runfunc(self):
        self.progress = "Working"
        try:
            fname = karaoke.Kareokise(self.title,self.artist,statusfunction=self.UpdateProgress)
        except:
            self.UpdateProgress("Failed")
            traceback.print_exc()
            return
        
        shutil.move(fname,"web/videos/" + fname)
        shutil.move("thumbnail.jpg","web/videos/" + fname.replace("mp4","jpg"))
        try:
            shutil.move("ytvideo.ass","web/videos/" + fname.replace("mp4","ass"))
        except:
            pass
        try:
            shutil.move(fname.replace("mp4","ogg"),"web/videos/" + fname.replace("mp4","ogg"))
        except:
            pass
        self.finalfile = fname;
        self.progress = "Complete"        
        ReloadSongs()
        CheckForNextJob()
        
    def Start(self):
        self.thread = threading.Thread(target=self.runfunc)
        self.thread.daemon = True
        self.thread.start()

class Song:
    def __init__(self,filename):
        self.artist = ""
        self.track = ""
        self.thumbnail = "/videos/" + filename.replace("mp4","jpg")
        self.status = "Ready"
        self.job = None
        self.path = filename
        self.version = 1
        self.age = 0
        
        global reftime
        
        nm = filename.replace(".mp4","")
        bits = nm.split(" - ")
        if len(bits) > 1:
            self.artist = bits[0].strip()
            self.track = bits[1].strip()
        else:
            self.track = bits[0]
            self.artist = "Unknown"
                
        if os.path.exists("web/videos/" + filename.replace(".mp4",".ogg")):
            self.version = 2

        self.age = int((time.time() - os.path.getctime("web/videos/" + filename)) / 86000)        
        print("Checking On " + "web/videos/" + filename.replace(".mp4",".ogg") + " " + str(self.age))
            
    def Get(self,nm):
        if nm == 'artist':
            return self.artist
        else:
            if nm == 'new':
                if self.age < 1:
                    return "Today"
                if self.age < 2:
                    return "Yesterday"
                if self.age < 7:
                    return "This Week"
                if self.age < 14:
                    return "This Fortnight"
                if self.age < 31:
                    return "This Month"
                if self.age < 365:
                    return "This Year"    
                return "Other"
            else:
                return self.track
        
songs = []

def ReloadSongs():
    global songs
    songs = []
    #print("Loading Songs...")
    for fl in glob.glob('web/videos/*.mp4'):
        #print(fl)
        songs.append(Song(os.path.basename(fl)))
    
ReloadSongs();

@app.route("/searchsong",methods = ['POST','GET'])
def songsearch():
    c = ConversionJob()
    print(str(request.form))
    c.title = request.form.get('track')
    c.artist = request.form.get('artist')
    conversions.append(c)
    
    print("Searching For " + c.title + " / " + c.artist)
    
    CheckForNextJob()
     
    return redirect("/")    

def GetQueueList():
    queuecontent = ""
    for q in conversions:
        if q.progress != "Complete" and q.progress != "Failed":
            queuecontent += '<div class="playListDark"><p>' + q.progress + '</p><p class="track">' + q.title + '</p><p class="artist">' + q.artist + '</p></div>'
        #else:
        #    queuecontent += '<div class="playListDark"><p><a href="/play?video=' + q.finalfile.replace("/mp4","") + '">PLAY</a></p><p class="track">' + q.title + '</p><p class="artist">' + q.artist + '</p></div>'    
    
    return queuecontent

@app.route("/queue")
def queuerequest():    
    return GetQueueList()

def artistsort(a):
    return a.artist

def titlesort(a):
    return a.track

def newsort(a):    
    return "{:06d}".format(a.age) + a.track

def GetSongList():
    
    sortorder = "artist"
    if request.args.get("sort") is not None:
        sortorder = request.args.get("sort")     
    #    session['sortorder'] = request.args.get("sort")        
    #else:
        #if 'sortorder' in session:
            #sortorder = session['sortorder']
    
    if sortorder == 'artist':
        songs.sort(key=artistsort)            
    else:
        if sortorder == 'new':
            songs.sort(key=newsort)
        else:
            songs.sort(key=titlesort)

    lastfirst = None
    queuecontent = ""
    indx = -1
    anyitems = False
    counter = 0
    for q in songs:
        indx += 1
        
        counter += 1
        
        if lastfirst is None or lastfirst != q.Get(sortorder)[0]:
            if lastfirst is not None:
                queuecontent += '</div>'
            counter = 0
            if sortorder == 'new':                
                queuecontent += '<div class="row sorting"><div class="col-md-12">' + q.Get(sortorder).upper() + '</div></div>';
            else:
                queuecontent += '<div class="row sorting"><div class="col-md-12">' + q.Get(sortorder).upper()[0] + '</div></div>';
            queuecontent += '<div class="row">'
            pass
            #if lastfirst is not None:
            #    queuecontent += "</div>"
            #queuecontent += '<div class="row sorting"><div class="col-md-12">' + q.Get(sortorder).upper()[0] + '</div></div>';
            #counter = 0
                    
        
        if counter > 0 and counter % 4 == 0:
            #if counter > 0:
            #    queuecontent += "</div>"
            queuecontent += '</div><div class="row">'
            
        anyitems = True
        if q.status != "Ready":
            queuecontent += '<div class="col-md-3"><a href="/play?video=' + q.path.replace(".mp4","") + '"><img class="thumb" src="' + q.thumbnail + '"/><div class="song"><div class="songinfo"><p class="track">' + q.track + '</p><p class="artist">' + q.artist + '</p><p class="state">' + q.state + '</p></div></div></a></div>'    
        else:
            queuecontent += '<div class="col-md-3"><a href="/play?video=' + q.path.replace(".mp4","") + '"><div class="song"><img class="thumb" src="' + q.thumbnail + '"/><div class="songinfo"><p class="track">' + q.track + '</p><p class="artist">' + q.artist + '</p></div></div></a></div>'    
            
        lastfirst = q.Get(sortorder)[0]
            
    if anyitems == True:
        queuecontent += "</div>"
    return queuecontent    

@app.route("/audiooffset")
def audiooffset():    
    newoffset = request.cookies.get('laoffset')
    if newoffset is None:
        newoffset = 0
    else:
        newoffset = float(newoffset)
        
    change = request.args.get('change')
    if change is None:
        newoffset = 0
    else:
        newoffset += float(change)
    resp = make_response(str(newoffset))
    resp.set_cookie('laoffset',str(newoffset))
    return resp

@app.route("/songs")
def songrequest():    
    return GetSongList()
    
@app.route("/play")
def playback():              
    
    chosen = None

    global songs
    for s in songs:
        if request.args.get('video') in s.path:
            chosen = s
            break
      
    if s.version == 2:
        fl = open('player2.html','r')
        rd = fl.read();
        fl.close();
    else:
        fl = open('player.html','r')
        rd = fl.read();
        fl.close();
            

    vurl = request.args.get('video')
    offset = 0
    
    jsnfile = os.path.dirname(__file__) + "/web/videos/" + chosen.path.replace(".mp4",".json")    
    if os.path.exists(jsnfile):
        fx = open(jsnfile,'r')
        content = fx.read()
        fx.close()
        md = json.loads(content)
        if 'lyricOffset' in md:
            if md['lyricOffset'] is not None:
                offset = -md['lyricOffset']
    
    laoffset = request.cookies.get('laoffset')
    if laoffset is None:
        laoffset = 0

    rd = rd.replace("[OFFSET]",str(offset))
    rd = rd.replace("[LAOFFSET]",str(laoffset))
    rd = rd.replace("[VIDEOFILE]",vurl)
    rd = rd.replace("[VIDEOSCRIPT]",vurl.replace("'","\\'"))
    rd = rd.replace("[VIDEOTITLE]",request.args.get('video'))
    return rd

@app.route("/findonline")
def findonline():       
    
    title = request.args.get('track')
    artist = request.args.get('artist')    

    song = karaoke.FindYTSong(title,artist)
           
    candidate = []    
    
    headers={ 'content-type':'application/json'}    
   
    if song is None:       
        return "[]",200,headers
    
    ob = {}
    ob['name'] = song.title
    ob['thumb'] = song.thumbnail_url
    candidate.append(ob)
        
    return json.dumps(candidate),200,headers
            
@app.route("/timing")
def timing():

    dta = request.args.get("video")        
    adjust = request.args.get("adjust")
    timing = request.args.get("timing")
    
    chosen = None

    global songs
    for s in songs:
        if request.args.get('video') in s.path:
            chosen = s
            break
        

    jsnfile = os.path.dirname(__file__) + "/web/videos/" + chosen.path.replace(".mp4",".json")    
    if timing is not None:
        #Get file offset...
        md = {}
        if os.path.exists(jsnfile):
            fx = open(jsnfile,'r')
            content = fx.read()
            fx.close()
            md = json.loads(content)        
            
        lyricfile = os.path.dirname(__file__) + "/web/videos/" + chosen.path.replace(".mp4",".ass")
        fl = open(lyricfile,'r')
        content = fl.read()
        fl.close()

        st = karaoke.GetAssLyricOffset(content)
        offset = float(timing) - st
        md['lyricOffset'] = offset
        
        print(str(timing) + " vs " + str(st))
        fx = open(jsnfile,'w')        
        fx.write(json.dumps(md))
        fx.flush()
        fx.close()
    else:
        md = {}
        if os.path.exists(jsnfile):
            fx = open(jsnfile,'r')
            content = fx.read()
            fx.close()
            md = json.loads(content)        
        else:
            md['lyricOffset'] = 0
                    
        if 'lyricOffset' not in md:
            md['lyricOffset'] = 0
            
        md['lyricOffset'] += float(adjust)
                
        fx = open(jsnfile,'w')        
        fx.write(json.dumps(md))
        fx.flush()
        fx.close()    

    return "/play/video=" + dta + "&timing=" + timing
    #return redirect("/play/video=" + dta + "&timing=" + timing)        

@app.route("/upgrade")
def upgrade():

    dta = request.args.get("name")    
    bits = dta.split(" - ")
    c = ConversionJob()    
    c.title = bits[1]
    c.artist = bits[0]
    conversions.append(c)
    
    print("Searching For " + c.title + " / " + c.artist)
    
    CheckForNextJob()
     
    return redirect("/")    

@app.route("/")
def hello_world():    
    
    return mainPage()