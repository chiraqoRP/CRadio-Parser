import io
import os
import re
import shutil

# Tinytag
from tinytag import Image as TImage, TinyTag

# Pillow
from PIL import Image

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import entities.station as station
    import entities.subplaylist as subplaylist

def SanitizeName(str):
    ## Filters out spaces
    str = re.sub(r'[^\w]', '_', str)

    ## Additionally filters out non-ASCII characters, as source doesn't like them.
    return re.sub(r'[^\x00-\x7F]+', '', str).lower()

class Song:
    def __init__(self, path: str, parent):
        self.Path = path
        _, self.FileType = os.path.splitext(path)

        self.URL: str | None = None
        self.Parent = parent
        self.Tags: TinyTag | None = None

        self.SafeName: str = ""
        self.SafeFileName: str = ""
        self.SafeRelease: str = ""

        self.CoverWritten: bool = False

    def __repr__(self):
        return f'Song("{self.GetArtist()}" - "{self.GetName()}")'

    def __eq__(self, other): 
        if other.Path == self.Path: 
            return True

        return False

    def GetName(self) -> str:
        return self.GetTags().title
    
    def GetSafeName(self) -> str:
        if not self.SafeName:
            ## Filters out dangerous characters
            self.SafeName = SanitizeName(self.GetName())

        return self.SafeName

    def GetSafeFileName(self) -> str:
        if not self.SafeFileName:
            ## Filters out dangerous characters
            self.SafeFileName = SanitizeName(self.GetArtist() + '_' + self.GetName())

        return self.SafeFileName
    
    def GetFileType(self) -> str:
        return self.FileType
    
    def GetSafeParentNames(self) -> tuple[str, str]:
        from entities.station import Station

        if isinstance(self.Parent, Station):
            return self.Parent.GetSafeName(), ""

        return self.GetStation().GetSafeName(), self.Parent.GetSafeName()

    def GetParent(self):
        return self.Parent
    
    def GetStation(self) -> "station.Station":
        from entities.station import Station

        if isinstance(self.Parent, Station):
            return self.Parent

        return self.Parent.GetStation()

    def GetArtist(self) -> str:
        return self.GetTags().artist

    def GetAlbumArtist(self) -> str:
        return self.GetTags().albumartist

    def GetRelease(self) -> str:
        return self.GetTags().album

    def GetLength(self) -> int:
        return round(self.GetTags().duration, 4)
        
    def GetCover(self):
        image: TImage | None = self.GetTags().images.any

        if not image:
            return

        ## We have to open the image as bytes
        return Image.open(io.BytesIO(image.data))
    
    def GetCoverName(self):
        if not self.SafeRelease:
            ## Filters out dangerous characters
            self.SafeRelease = SanitizeName(self.GetAlbumArtist() + '_' + self.GetRelease())

        return self.SafeRelease
    
    def GetCoverPath(self) -> tuple[str, str, bool]:
        ## Filters out dangerous characters before joining our path
        matPath = os.path.join("cradio", "covers", *self.GetSafeParentNames(), self.GetCoverName() + ".png")
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

    def GetSoundPath(self, shouldMakeFolder: bool = True) -> tuple[str, str]:
        ## Filters out dangerous characters before joining our path
        soundPath = os.path.join("sound", "cradio", "stations", *self.GetSafeParentNames(), self.GetSafeFileName() + self.GetFileType())
        filePath = os.path.join("cradio_songs", soundPath)

        ## Source uses forward slashes, but some OSes will use backslashes.
        if os.sep != '/':
            soundPath = soundPath.replace(os.sep, '/')

        if not shouldMakeFolder:
            return filePath, soundPath

        folderPath = os.path.dirname(filePath)

        if not os.path.exists(folderPath):
            os.makedirs(folderPath)

        return filePath, soundPath

    def GetTags(self) -> TinyTag | None:
        if self.Tags:
            return self.Tags

        try:
            self.Tags = TinyTag.get(self.Path, image=True)
        except TypeError:
            print("Missing ID3 tags in ", os.path.basename(self.Path), ", skipping it.")

            return None

        return self.Tags

    WriteFormat = '''CRadio:Song("{0}", {{
    Artist = "{1}",
    {2},
    Length = {3:.3f},
    {4},
    {5}
    {6}
    Parent = {7}
}})\n\n'''

    def Write(self):
        name = self.GetName()

        if not name:
            return False
        
        print("Writing ", self.Path)

        parser = self.GetStation().GetParser()

        if parser.GetUploader():
            self.URL = parser.UploadFile(self.Path)

        release = self.GetRelease()
        soundPath, coverPath = self.WriteAudio(), self.WriteCover()
        content = self.WriteFormat.format(
            name,
            self.GetArtist(),
            ## Checks for self-titled releases
            'Release = true' if name == release else f'Release = "{release}"',
            self.GetLength(),
            f'File = "{soundPath}"',
            f'URL = "{self.URL}",' if self.URL else '',
            f'Cover = "{coverPath}",' if self.CoverWritten else '',
            self.GetParent().GetVar()
        )

        ## We remove empty lines this way.
        content = content.replace('\n    \n', '\n')

        stationFile = self.GetStation().GetFile()
        stationFile.write(content)

        return True

    CoverFormat = 'song:SetCover("{0}")\n'
    CoverSize = [128, 128]

    def WriteCover(self) -> str | None:
        path, matPath, self.CoverWritten = self.GetCoverPath()

        if not self.CoverWritten:
            image = self.GetCover()

            if not image:
                return

            ## Lanczos is the best algorithm for downscaling images, gmod's in-engine solution is terrible
            image.thumbnail(self.CoverSize, Image.Resampling.LANCZOS)
            image.save(path, "PNG")
            image.close()

            self.CoverWritten = True

        return matPath

    URLFormat = 'song:SetURL("{0}")\n'
    FileFormat = 'song:SetFile("{0}")\n'

    def WriteAudio(self) -> str:
        destination, soundPath = self.GetSoundPath(not self.URL)

        if not self.URL:
            shutil.copyfile(self.Path, destination)

        return soundPath