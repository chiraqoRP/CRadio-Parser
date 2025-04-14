import io
import os
import sys
import requests

from typing import TYPE_CHECKING
from collections.abc import Callable

if TYPE_CHECKING:
    import entities.station as station

UploadTuple = tuple[requests.Response, str]

class Parser:
    def __init__(self, workFolder):
        self.UploaderFuncs: list[function] = [self.DoCatboxUpload, self.DoPomfUpload, self.DoPomfUpload, self.DoMonofileUpload]
        self.UploaderIndex: int | None = None

        ## COMMENT
        self.MainDir, self.MadeDirs = workFolder, False

        self.FetchStations()

    def GetMainDirectory(self) -> str:
        return self.MainDir
    
    def GetStationsDirectory(self) -> str:
        return os.path.join(self.GetMainDirectory(), "cradio_stations")
    
    def GetFilesDirectory(self) -> str:
        return os.path.join(self.GetMainDirectory(), "cradio_songs", "sound", "cradio", "stations")

    def GetUploader(self) -> Callable:
        if not self.UploaderIndex:
            return None

        return self.UploaderFuncs[self.UploaderIndex - 1]

    def SetUploader(self, index: int):
        self.UploaderIndex = index

    def GetUserHash(self) -> str:
        return self.UserHash

    def SetUserHash(self, userHash: str):
        self.UserHash = userHash

    def GetStations(self) -> list["station.Station"]:
        return self.Stations
    
    def FetchStations(self):
        from entities.station import Station

        self.Stations: list["station.Station"] = []

        for i in range(1, len(sys.argv)):
            folder = sys.argv[i]
            station = Station(folder, self)

            self.Stations.append(station)

    def DoParse(self):
        stations = self.GetStations()

        if not stations:
            print("No folders were input.")

            return
        
        if not self.MadeDirs:
            stationDirs = os.path.join(self.GetStationsDirectory(), "lua", "cradio", "shared", "stations")

            os.makedirs(stationDirs, exist_ok = True)

            if not self.GetUploader():
                os.makedirs(self.GetFilesDirectory(), exist_ok = True)

            self.MadeDirs = True
        
        for station in stations:
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
                sizeLimit = self.UploaderLimits[self.UploaderIndex - 1]

                if os.path.getsize(path) > sizeLimit:
                    return None

                ## Start uploading our file, this is not done with another thread so each file must be uploaded one-by-one.
                uploader = self.GetUploader()
                response, url = uploader(file.read(), path)

                if response.status_code == 200:
                    print(self.UploadSuccessFormat.format(path))
                else:
                    print(self.UploadFailureFormat.format(path, str(response.status_code)))

                return url
        except Exception as e:
            print(self.UploadExceptionFormat.format(path, str(e)))

    def DoCatboxUpload(self, file: bytes, path) -> UploadTuple:
        # -----------------------------9675585837039348863164086322
        # Content-Disposition: form-data; name="fileToUpload"; filename="the_stack.png"
        # Content-Type: image/png

        _, fileType = os.path.splitext(path)

        files = {
            'reqtype': (None, 'fileupload'),
            'userhash': (None, self.UserHash),
            'fileToUpload': (f'file.{fileType[1:]}', file),
        }

        response = requests.post("https://catbox.moe/user/api.php", files = files)

        try:
            return response, response.text
        except:
            return response, ""

    PomfHosts = {
        1: "https://pomf.lain.la/upload.php",
        2: "https://qu.ax/upload.php"
    }

    def DoPomfUpload(self, file: bytes, path) -> UploadTuple:
        # -----------------------------426483243616972780734144962905
        # Content-Disposition: form-data; name="files[]"; filename="rain_temple.png"
        # Content-Type: image/png

        files = {
            "files[]": (path, file)
        }

        response = requests.post(self.PomfHosts[self.UploaderIndex - 1], files = files)

        try:
            return response, response.json()["files"][0]["url"]
        except:
            return response, ""

    MonofileAuthFormat = "auth={0}"
    MonofileURLFormat = "https://fyle.uk/download/{0}"

    def DoMonofileUpload(self, file: bytes, path: str) -> UploadTuple:
        # -----------------------------28294015417419468024143018187
        # Content-Disposition: form-data; name="file"; filename="rain_temple.png"
        # Content-Type: image/png

        headers = {
            "Cookie": self.MonofileAuthFormat.format(self.UserHash)
        }

        files = {
            "file": (path, file)
        }

        response = requests.post("https://fyle.uk/upload", files = files, headers = headers)

        try:
            return response, self.MonofileURLFormat.format(response.text)
        except:
            return response, ""