# Standard libraries
import io, os, sys, re, shutil

# Requests
import requests

# Tinytag
from tinytag import TinyTag

# Pillow
from PIL import Image

cParser = None

def SanitizeName(str):
    ## Filters out spaces
    str = re.sub(r'[^\w]', '_', str)

    ## Additionally filters out non-ASCII characters, as source doesn't like them.
    return re.sub(r'[^\x00-\x7F]+', '', str).lower()

class Parser:
    def __init__(self, workFolder):
        self.UploaderFuncs = [self.DoCatboxUpload, self.DoPomfUpload, self.DoPomfUpload, self.DoMonofileUpload]
        self.UploaderIndex = None

        ## COMMENT
        self.MainDir, self.MadeDirs = workFolder, False

        self.FetchStations()

    def GetMainDirectory(self):
        return self.MainDir
    
    def GetStationsDirectory(self):
        return os.path.join(self.GetMainDirectory(), "cradio_stations")
    
    def GetFilesDirectory(self):
        return os.path.join(self.GetMainDirectory(), "cradio_songs", "sound", "cradio", "stations")

    def GetUploader(self):
        if not self.UploaderIndex:
            return None

        return self.UploaderFuncs[self.UploaderIndex - 1]

    def SetUploader(self, index):
        self.UploaderIndex = index

    def GetUserHash(self):
        return self.UserHash

    def SetUserHash(self, userHash):
        self.UserHash = userHash

    def GetStations(self):
        return self.Stations
    
    def FetchStations(self):
        self.Stations = []

        for i in range(1, len(sys.argv)):
            folder = sys.argv[i]
            station = Station(folder)

            self.Stations.append(station)

    def DoParse(self):
        if not self.Stations:
            print("No folders were input.")

            return
        
        if not self.MadeDirs:
            stationDirs = os.path.join(self.GetStationsDirectory(), "lua", "cradio", "shared", "stations")

            os.makedirs(stationDirs, exist_ok=True)

            if not self.GetUploader():
                os.makedirs(self.GetFilesDirectory(), exist_ok=True)

            self.MadeDirs = True
        
        for station in self.Stations:
            station.Write()

    UploadSuccessFormat = "Upload successful for file [{0}]!"
    UploadFailureFormat = "Upload failed for file [{0}], received response {1}!"
    UploadExceptionFormat = "Upload failed for file [{0}], {1}!"

    ## In bytes
    UploaderLimits = [200000000, 1000000000, 100000000, 754974700]

    def UploadFile(self, path):
        if not self.UploaderIndex:
            return None

        try:
            with io.open(path, "rb") as file:
                ## print(userHash)

                sizeLimit = self.UploaderLimits[self.UploaderIndex - 1]

                if os.path.getsize(path) > sizeLimit:
                    return None

                ## print("before post")

                ## Start uploading our file, this is not done with another thread so each file must be uploaded one-by-one.
                uploader = self.GetUploader()
                response, url = uploader(file, path)

                ## print("after post")

                if response.status_code == 200:
                    print(self.UploadSuccessFormat.format(path))
                else:
                    print(self.UploadFailureFormat.format(path, str(response.status_code)))

                return url
        except Exception as e:
            print(self.UploadExceptionFormat.format(path, str(e)))

    def DoCatboxUpload(self, file, path):
        # -----------------------------9675585837039348863164086322
        # Content-Disposition: form-data; name="fileToUpload"; filename="the_stack.png"
        # Content-Type: image/png

        _, fileType = os.path.splitext(path)

        files = {
            'reqtype': (None, 'fileupload'),
            'userhash': (None, self.UserHash),
            'fileToUpload': (f'file.{fileType[1:]}', file.read()),
        }

        response = requests.post("https://catbox.moe/user/api.php", files=files)

        try:
            return response, response.text
        except:
            return response, None

    PomfHosts = {
        1: "https://pomf.lain.la/upload.php",
        2: "https://qu.ax/upload.php"
    }

    def DoPomfUpload(self, file, path):
        # -----------------------------426483243616972780734144962905
        # Content-Disposition: form-data; name="files[]"; filename="rain_temple.png"
        # Content-Type: image/png

        files = {
            "files[]": (path, file.read())
        }

        response = requests.post(self.PomfHosts[self.UploaderIndex - 1], files=files)

        try:
            return response, response.json()["files"][0]["url"]
        except:
            return response, None

    MonofileAuthFormat = "auth={0}"
    MonofileURLFormat = "https://fyle.uk/download/{0}"

    def DoMonofileUpload(self, file, path):
        # -----------------------------28294015417419468024143018187
        # Content-Disposition: form-data; name="file"; filename="rain_temple.png"
        # Content-Type: image/png

        headers = {
            "Cookie": self.MonofileAuthFormat.format(self.UserHash)
        }

        files = {
            "file": (path, file.read())
        }

        response = requests.post("https://fyle.uk/upload", files=files, headers=headers)

        try:
            return response, self.MonofileURLFormat.format(response.text)
        except:
            return response, None

validFileTypes = [".mp3", ".ogg", ".flac"]

class Station:
    def __init__(self, path):
        self.Path = path
        self.Name = os.path.basename(path)

        ## Filters out dangerous characters
        self.SafeName = SanitizeName(self.Name)

        self.FetchObjects()

    def __repr__(self):
        return f'Station("{self.Name}")'

    def __eq__(self, other): 
        if isinstance(other, Station) and other.Name == self.Name: 
            return True

        return False

    def GetName(self):
        return self.Name

    def GetSafeName(self):
        return self.SafeName

    def GetVar(self):
        return "station"

    def GetFile(self):
        return self.File

    def GetLuaPath(self):
        return os.path.join(cParser.GetStationsDirectory(), "lua", "cradio", "shared", "stations", self.GetSafeName() + ".lua")

    def GetIcon(self):
        for name in self.DirectoryTree:
            _, fileType = os.path.splitext(name)

            if fileType == ".png":
                return os.path.join(self.Path, name)

        return None
    
    def GetIconPath(self):
        ## Filters out dangerous characters before joining our path
        matPath = os.path.join("cradio", "stations", self.GetSafeName() + ".png")
        filePath = os.path.join(cParser.GetStationsDirectory(), "materials", matPath)

        ## Source uses forward slashes, but some OSes will use backslashes.
        if os.sep != '/':
            matPath = matPath.replace(os.sep, '/')

        folderPath = os.path.dirname(filePath)

        if not os.path.exists(folderPath):
            os.makedirs(folderPath)

        return filePath, matPath

    def GetSongs(self):
        return self.Songs
    
    def GetSubPlaylists(self):
        return self.SubPlaylists

    def FetchObjects(self):
        self.Songs = []
        self.SubPlaylists = []

        try:
            self.DirectoryTree = os.listdir(self.Path)

            ## print("fileNames: ", fileNames)

            for name in self.DirectoryTree:
                _, fileType = os.path.splitext(name)
                isFolder = os.path.isdir(name)

                ## We don't want to include sub-playlists.
                if not isFolder and fileType not in validFileTypes:
                    continue

                oPath = os.path.join(self.Path, name)

                ## print("songPath", songPath)

                if isFolder:
                    subPlaylist = SubPlaylist(oPath, self)

                    self.SubPlaylists.append(subPlaylist)
                else:
                    song = Song(oPath, self)

                    self.Songs.append(song)
        except IOError:
            print("Failed to open directory: ", self.Path)

    StartingLine = "---------------------------------\n-- Station\n---------------------------------\n"
    SongLine = "---------------------------------\n-- Songs\n---------------------------------\n"
    StationFormat = 'local station = CRadio:Station("{0}")\n'
    IconFormat = 'station:SetIcon("{0}")\n\n'

    def Write(self):
        ## Gets the list of all music files and folders.
        songs, subPlaylists = self.GetSongs(), self.GetSubPlaylists()

        if not songs and not subPlaylists:
            return False

        ## print("fileList", fileList)

        name = self.GetName()

        with io.open(self.GetLuaPath(), "w", encoding="utf-8") as self.File:
            self.File.write(self.StartingLine)
            self.File.write(self.StationFormat.format(name))

            self.WriteIcon()

            self.File.write(self.SongLine)

            for song in songs:
                song.Write()

            for subPlaylist in subPlaylists:
                subPlaylist.Write()

    def WriteIcon(self):
        icon = self.GetIcon()

        if not icon:
            return

        destination, matPath = self.GetIconPath()

        shutil.copyfile(icon, destination)

        self.File.write(self.IconFormat.format(matPath))
    
class Song:
    def __init__(self, path, parent):
        self.Path = path
        _, self.FileType = os.path.splitext(path)

        self.URL = None
        self.Parent = parent

    def __repr__(self):
        return f'Song("{self.GetArtist()}"- "{self.GetName()}")'

    def __eq__(self, other): 
        if isinstance(other, Song) and other.Path == self.Path: 
            return True

        return False

    def GetName(self):
        return self.GetTags().title
    
    def GetSafeName(self):
        if not hasattr(self, 'SafeName'):
            ## Filters out dangerous characters
            self.SafeName = SanitizeName(self.GetName())

        return self.SafeName

    def GetSafeFileName(self):
        if not hasattr(self, 'SafeFileName'):
            ## Filters out dangerous characters
            self.SafeFileName = SanitizeName(self.GetArtist() + '_' + self.GetName())

        return self.SafeFileName
    
    def GetFileType(self):
        return self.FileType
    
    def GetSafeParentNames(self):
        if isinstance(self.Parent, Station):
            return self.Parent.GetSafeName(), ""

        return self.GetStation().GetSafeName(), self.Parent.GetSafeName()

    def GetParent(self):
        return self.Parent
    
    def GetStation(self):
        if isinstance(self.Parent, Station):
            return self.Parent
        
        return self.Parent.GetStation()

    def GetArtist(self):
        return self.GetTags().artist

    def GetRelease(self):
        return self.GetTags().album

    def GetLength(self):
        return round(self.GetTags().duration, 4)
        
    def GetCover(self):
        if not hasattr(self, 'Cover'):
            image = self.GetTags().get_image()

            if image:
                ## We have to open the image as bytes
                self.Cover = Image.open(io.BytesIO(image))

        return self.Cover
    
    def GetCoverName(self):
        if not hasattr(self, 'SafeRelease'):
            ## Filters out dangerous characters
            self.SafeRelease = SanitizeName(self.GetArtist() + '_' + self.GetRelease())

        return self.SafeRelease
    
    def GetCoverPath(self):
        ## Filters out dangerous characters before joining our path
        matPath = os.path.join("cradio", "covers", self.GetStation().GetSafeName(), self.GetCoverName() + ".png")
        coverPath = os.path.join("cradio_covers", "materials", matPath)

        ## Source uses forward slashes, but some OSes will use backslashes.
        if os.sep != '/':
            matPath = matPath.replace(os.sep, '/')

        ## If a cover has already been saved for this song, just reuse it.
        if os.path.isfile(coverPath):
            return coverPath, matPath, True
        
        folderPath = os.path.dirname(coverPath)

        if not os.path.exists(folderPath):
            os.makedirs(folderPath)

        return coverPath, matPath, False

    def GetSoundPath(self):
        ## Filters out dangerous characters before joining our path
        soundPath = os.path.join("sound", "cradio", "stations", *self.GetSafeParentNames(), self.GetSafeFileName() + self.GetFileType())
        filePath = os.path.join("cradio_songs", soundPath)

        ## Source uses forward slashes, but some OSes will use backslashes.
        if os.sep != '/':
            soundPath = soundPath.replace(os.sep, '/')

        folderPath = os.path.dirname(filePath)

        if not os.path.exists(folderPath):
            os.makedirs(folderPath)

        return filePath, soundPath

    def GetTags(self):
        if hasattr(self, "Tags"):
            return self.Tags

        try:
            self.Tags = TinyTag.get(self.Path, image=True)
        except TypeError:
            print("Missing ID3 tags in ", os.path.basename(self.Path), ", skipping it.")

            return None

        return self.Tags

    MainFormat = 'local song = CRadio:Song("{0}")\n'
    ArtistFormat = 'song:SetArtist("{0}")\n'
    ReleaseFormat = 'song:SetRelease("{0}")\n'
    LengthFormat = 'song:SetLength({0:.4f})\n'
    ParentFormat = "song:SetParent({0})\n\n"

    def Write(self):
        name = self.GetName()

        if not name:
            return False
        
        print("Writing ", self.Path)

        if cParser.GetUploader():
            self.URL = cParser.UploadFile(self.Path)

        stationFile = self.GetStation().GetFile()
        stationFile.write(self.MainFormat.format(name))
        stationFile.write(self.ArtistFormat.format(self.GetArtist()))

        release = self.GetRelease()

        ## Checks for self-titled releases
        if name == release:
            stationFile.write('song:SetRelease(true)\n')
        else:
            stationFile.write(self.ReleaseFormat.format(release))

        stationFile.write(self.LengthFormat.format(self.GetLength()))

        self.WriteAudio()
        self.WriteCover()

        parent = self.GetParent().GetVar()

        stationFile.write(self.ParentFormat.format(parent))

        return True

    CoverFormat = 'song:SetCover("{0}")\n'
    CoverSize = [128, 128]

    def WriteCover(self):
        path, matPath, alreadyPresent = self.GetCoverPath()

        if not alreadyPresent:
            image = self.GetCover()

            if not image:
                return

            ## Lanczos is the best algorithm for downscaling images, gmod's in-engine solution is terrible
            image.thumbnail(self.CoverSize, Image.Resampling.LANCZOS)
            image.save(path, "PNG")

        stationFile = self.GetStation().GetFile()
        stationFile.write(self.CoverFormat.format(matPath))

    URLFormat = 'song:SetURL("{0}")\n'
    FileFormat = 'song:SetFile("{0}")\n'

    def WriteAudio(self):
        stationFile = self.GetStation().GetFile()

        if self.URL:
            stationFile.write(self.URLFormat.format(self.URL))

            return

        destination, soundPath = self.GetSoundPath()

        shutil.copyfile(self.Path, destination)

        stationFile.write(self.FileFormat.format(soundPath))
    
class SubPlaylist:
    def __init__(self, path, parent):
        self.Path = path
        self.Name = os.path.basename(path)
        self.SafeName = SanitizeName(self.Name)

        self.Parent = parent

    def __repr__(self):
        return f'SubPlaylist("{self.Parent.GetName()}"- "{self.GetName()}")'

    def __eq__(self, other): 
        if isinstance(other, Song) and other.Name == self.Name:
            return True

        return False

    def GetName(self):
        return self.Name

    def GetSafeName(self):
        return self.SafeName
    
    def GetParent(self):
        return self.Parent
    
    def GetStation(self):
        return self.Parent
    
    def GetVar(self):
        return self.GetSafeName() + "Playlist"

    def GetSongs(self):
        return self.Songs
    
    def FetchSongs(self):
        self.Songs = []

        try:
            for name in self.DirectoryTree:
                _, fileType = os.path.splitext(name)

                ## We don't want to include sub-playlists.
                if os.path.isdir(name) or fileType not in validFileTypes:
                    continue

                songPath = os.path.join(self.Path, name)

                ## print("songPath", songPath)

                song = Song(songPath, self)

                self.Songs.append(song)
        except IOError:
            print("Failed to open directory: ", self.Path)

        return self.Songs

    InfoLine = "\n---------------------------------\n-- {0} (Playlist)\n---------------------------------\n"
    MainFormat = 'local {0}Playlist = CRadio:SubPlaylist("{0}")\n'
    ParentFormat = '{0}Playlist:SetParent(station)\n\n'

    def Write(self):
        name = self.GetName()

        stationFile = self.GetStation().GetFile()
        stationFile.write(self.InfoLine.format(name))
        stationFile.write(self.MainFormat.format(name))
        stationFile.write(self.ParentFormat.format(self.GetStation().GetVar()))

        ## print("musicList: ", musicList)

        for song in self.GetSongs():
            ## print("subSong: ", song)

            self.WriteSong(song)

def AskForUserHash(hostIndex):
    ## catbox.moe and Monofile have an account system.
    authAccepted = hostIndex == 1 or hostIndex == 3

    ## Monofile requires an account to upload to
    authRequired = hostIndex == 3
    userHash = ""

    if authAccepted:
        print("---------------------------------")

        ## Some hosts require a userhash token.
        if authRequired:
            print("Do you have a userhash? (This is required for your host!)")
        else:
            print("Do you have a userhash you wish to use? (Leave empty for none)")

        userHash = input()

        ## Keep asking for a userhash token if one is required.
        if userHash == "" and authRequired:
            AskForUserHash(hostIndex)

            return
        
        cParser.SetUserHash(userHash)

        print("userHash", userHash)

        ## Start making our station file(s).
        cParser.DoParse()
    else:
        ## Start making our station file(s).
        cParser.DoParse()

if __name__ == "__main__":
    workDir = os.path.dirname(os.path.abspath(__file__))
    cParser = Parser(workDir)

    print("---------------------------------")
    print("Do you want to upload these files onto a host?")

    doUpload = input("(Y/N): ")

    if doUpload.lower() == "y":
        print("---------------------------------")
        print("Which host? If you are unsure, select 1.")
        print("[1] - catbox.moe")
        print("[2] - pomf.lain.la")
        print("[3] - qu.ax")
        print("[4] - Monofile")

        ## Clamps between min and max host to prevent out of range index.
        hostIndex = max(1, min(int(input("(x): ")), 4))
        cParser.SetUploader(hostIndex)

        AskForUserHash(hostIndex)
    else:
        ## Start making our station file(s).
        cParser.DoParse()