# Standard libraries
import io, os, sys, re

# Requests
import requests

# Tinytag
from tinytag import TinyTag

# Pillow
from PIL import Image

successFormat = "Upload successful for file [{0}]!"
failureFormat = "Upload failed for file [{0}], received response {1}!"
exceptionFormat = "Upload failed for file [{0}], exception {1} raised!"

def DoCatboxUpload(file, path, userHash):
    # -----------------------------9675585837039348863164086322
    # Content-Disposition: form-data; name="reqtype"

    # fileupload
    # -----------------------------9675585837039348863164086322
    # Content-Disposition: form-data; name="userhash"

    # -----------------------------9675585837039348863164086322
    # Content-Disposition: form-data; name="fileToUpload"; filename="the_stack.png"
    # Content-Type: image/png

    _, fileType = os.path.splitext(path)

    files = {
        'reqtype': (None, 'fileupload'),
        'userhash': (None, userHash),
        'fileToUpload': (f'file.{fileType[1:]}', file.read()),
    }

    response = requests.post("https://catbox.moe/user/api.php", files=files)

    try:
        return response, response.text
    except:
        return response, None

def DoPomfUpload(file, path, userHash):
    # -----------------------------426483243616972780734144962905
    # Content-Disposition: form-data; name="files[]"; filename="rain_temple.png"
    # Content-Type: image/png

    files = {
        "files[]": (path, file.read())
    }

    response = requests.post("https://pomf.lain.la/upload.php", files=files)

    try:
        return response, response.json()["files"][0]["url"]
    except:
        return response, None

def DoQuaxUpload(file, path, userHash):
    # -----------------------------97370897018657600161858382728
    # Content-Disposition: form-data; name="files[]"; filename="rain_temple.png"
    # Content-Type: image/png

    files = {
        "files[]": (path, file.read())
    }

    response = requests.post("https://qu.ax/upload.php", files=files)

    try:
        return response, response.json()["files"][0]["url"]
    except:
        return response, None

monoAuth = "auth={0}"
monoUrl = "https://fyle.uk/download/{0}"

def DoMonofileUpload(file, path, userHash):
    # -----------------------------28294015417419468024143018187
    # Content-Disposition: form-data; name="file"; filename="rain_temple.png"
    # Content-Type: image/png

    headers = {
        "Cookie": monoAuth.format(userHash)
    }

    files = {
        "file": (path, file.read())
    }

    response = requests.post("https://fyle.uk/upload", files=files, headers=headers)

    try:
        return response, monoUrl.format(response.text)
    except:
        return response, None

uploaderFuncs = [DoCatboxUpload, DoPomfUpload, DoQuaxUpload, DoMonofileUpload]

## MiBs
uploaderLimits = [200000000, 1000000000, 100000000, 754974700]

def DoFileUpload(path):
    try:
        with io.open(path, "rb") as file:
            ## print(userHash)

            fileSize = os.path.getsize(path)

            sizeLimit = uploaderLimits[hostIndex - 1]

            if fileSize > sizeLimit:
                return None

            doUploadFunc = uploaderFuncs[hostIndex - 1]

            ## print("before post")

            ## Start uploading our file, this is not done with another thread so each file must be uploaded one-by-one.
            response, url = doUploadFunc(file, path, userHash)

            ## print("after post")

            if response.status_code == 200:
                print(successFormat.format(path))
            else:
                print(failureFormat.format(path, str(response.status_code)))

            return url
    except Exception as e:
        print(exceptionFormat.format(path, str(e)))

maxSize = [128, 128]

def GetFileTags(file):
    try:
        print(file)

        sCoverName = None

        mFile = TinyTag.get(file, image=True)
        image = mFile.get_image()

        if image is not None:
            ## Filters out dangerous characters before creating our path
            coverName = re.sub(r'[^\w]', '', mFile.artist + "_" + mFile.album).lower()
            folderPath = os.path.join("covers", "materials", "cradio", "covers")
            coverPath = os.path.join(folderPath, coverName + ".png")

            ## If we have a cover we need to write the string to our lua file
            sCoverName = coverName + ".png"

            ## If a cover has already been saved for this song, just reuse it.
            if os.path.isfile(coverPath):
                return mFile.title, mFile.artist, mFile.album, mFile.duration, sCoverName, os.path.basename(file)

            ## Write our folder for covers if it doesn't exist
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)

            ## We have to open the image as bytes
            imageBytes = io.BytesIO(image)

            coverImage = Image.open(imageBytes)

            ## Lanczos is the best algorithm for downscaling images, gmod's in-engine solution is terrible
            coverImage.thumbnail(maxSize, Image.Resampling.LANCZOS)
            coverImage.save(coverPath, "PNG")

        return mFile.title, mFile.artist, mFile.album, mFile.duration, sCoverName, os.path.basename(file)
    except TypeError:
       print("Missing ID3 tags in ", file, ", skipping it.")

       return None

songLocalFormat = 'local song = CRadio:Song("{0}")\n'
songFormat = 'song = CRadio:Song("{0}")\n'
artistFormat = 'song:SetArtist("{0}")\n'
releaseFormat = 'song:SetRelease("{0}")\n'
lengthFormat = 'song:SetLength({0:.4f})\n'
urlFormat = 'song:SetURL("{0}")\n'
fileFormat = 'song:SetFile("{0}")\n'
coverFormat = 'song:SetCover("{0}")\n'
parentStr = "song:SetParent({0})\n"
uploadFunc = None

def WriteSong(song, stationFile, stationName, doLocal=False, parent=None):
    songName, artist, release, length, coverName, file = GetFileTags(song)

    if songName is None:
        return False

    url = None

    if hostIndex is not None:
        url = DoFileUpload(song)

    firstLine = songFormat.format(songName)

    if doLocal:
        firstLine = "local " + firstLine

    stationFile.write(firstLine)
    stationFile.write(artistFormat.format(artist))
    stationFile.write(releaseFormat.format(release))
    stationFile.write(lengthFormat.format(length))

    if url is not None:
        stationFile.write(urlFormat.format(url))
    else:
        soundPath = os.path.join("sound", "cradio", "stations", stationName, file)
        soundPath = soundPath.replace(os.sep, '/')

        stationFile.write(fileFormat.format(soundPath))

    if coverName is not None:
        coverPath = os.path.join("cradio", "covers", coverName)
        coverPath = coverPath.replace(os.sep, '/')

        stationFile.write(coverFormat.format(coverPath))

    if not parent:
        parent = "station"

    stationFile.write(parentStr.format(parent))

    return True

audioFileTypes = [".mp3", ".ogg", ".flac"]

def GetMusicFiles(path, ignoreFolders=False):
    try:
        musicList = []
        playlistList = []
        fileNames = os.listdir(path)

        ## print("fileNames: ", fileNames)

        for fileName in fileNames:
            _, fileType = os.path.splitext(fileName)
            isFolder = os.path.exists(os.path.dirname(fileName))

            ## This is used for when we don't want to include sub-playlists.
            if isFolder and ignoreFolders:
                continue

            if not isFolder and fileType not in audioFileTypes:
                continue

            filePath = os.path.join(path, fileName)

            ## print("filePath", filePath)

            if isFolder:
                playlistList.insert(-1, filePath)
            else:
                musicList.insert(-1, filePath)

        ## print(musicList)

        return musicList, playlistList
    except:
        print("Failed to open directory: ", path)

        return [], []

subPlaylistLine = "\n---------------------------------\n-- {0} (Playlist)\n---------------------------------\n"
subPlaylistFormat = 'local {0}Playlist = CRadio:SubPlaylist("{0}")\n'
subParentFormat = '{0}Playlist:SetParent(station)\n\n'

def WriteSubplaylist(subPlaylist, stationFile, stationName):
    musicList, _ = GetMusicFiles(subPlaylist, True)
    subPlaylistName = os.path.basename(subPlaylist)

    stationFile.write(subPlaylistLine.format(subPlaylistName))
    stationFile.write(subPlaylistFormat.format(subPlaylistName))
    stationFile.write(subParentFormat.format(subPlaylistName))

    parentName = subPlaylistName + "Playlist"
    songCount = len(musicList)
    currentIteration = 0

    ## print("musicList: ", musicList)

    for song in musicList:
        ## print("subSong: ", song)
        successful = WriteSong(song, stationFile, stationName, currentIteration == 0, parentName)

        if currentIteration != songCount - 1:
            stationFile.write("\n")

        if successful:
            currentIteration += 1

startingLine = "---------------------------------\n-- Station\n---------------------------------\n"
songLine = "---------------------------------\n-- Songs\n---------------------------------\n"
stationFormat = 'local station = CRadio:Station("{0}")\n'
iconFormat = 'station:SetIcon("{0}.png")\n\n'

def WriteStation(fileList, playlistList, name="DefaultName"):
    fileName = re.sub(r'[^\w]', '', name).lower()

    stationFile = io.open(fileName + ".lua", "w", encoding="utf-8")
    stationFile.write(startingLine)
    stationFile.write(stationFormat.format(name))

    name = name.lower()

    iconPath = os.path.join("cradio", "stations", fileName)
    iconPath = iconPath.replace(os.sep, '/')

    stationFile.write(iconFormat.format(iconPath))
    stationFile.write(songLine)

    songCount = len(fileList)
    currentIteration = 0

    for song in fileList:
        successful = WriteSong(song, stationFile, name, currentIteration == 0)

        if currentIteration != songCount - 1:
            stationFile.write("\n")

        if successful:
            currentIteration += 1

    for subPlaylist in playlistList:
        WriteSubplaylist(subPlaylist, stationFile, name)

    stationFile.close()

def DoParse():
    for i in range(1, len(sys.argv)):
        directoryPath = sys.argv[i]
        stationName = os.path.basename(directoryPath)

        ## print("path: ", directoryPath)

        ## Gets the list of all music files and folders.
        musicList, playlistList = GetMusicFiles(directoryPath)

        ## print("fileList", fileList)

        ## Constructs and writes our station's lua file, then uploads songs if needed.
        WriteStation(musicList, playlistList, stationName)

def AskForUserHash(authAccepted, authRequired):
    # Declared as global because this var gets carried through a ton of functions otherwise
    global userHash
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
            AskForUserHash(authAccepted, authRequired)

            return

        print("userHash", userHash)

        ## Start making our station file(s).
        DoParse()
    else:
        ## Start making our station file(s).
        DoParse()

def AskForOptions():
    # Declare hostIndex as global
    global hostIndex
    hostIndex = None

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

        ## catbox.moe and qu.ax have an account system.
        authAccepted = hostIndex == 1 or hostIndex == 3

        ## qu.ax requires an account to upload to
        authRequired = hostIndex == 3

        AskForUserHash(authAccepted, authRequired)
    else:
        ## Start making our station file(s).
        DoParse()

if __name__ == "__main__":
    AskForOptions()