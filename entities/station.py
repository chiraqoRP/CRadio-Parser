import io
import os
import re
import shutil

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import parser
    import entities.song as song
    import entities.subplaylist as subplaylist

def SanitizeName(str):
    ## Filters out spaces
    str = re.sub(r'[^\w]', '_', str)

    ## Additionally filters out non-ASCII characters, as source doesn't like them.
    return re.sub(r'[^\x00-\x7F]+', '', str).lower()

validFileTypes = [".mp3", ".ogg", ".flac"]

class Station:
    def __init__(self, path: str, parser: "parser.Parser"):
        self.Parser = parser
        self.Path = path
        self.Name = os.path.basename(path)

        ## Filters out dangerous characters
        self.SafeName = SanitizeName(self.Name)

        self.Songs: list["song.Song"] = []
        self.SubPlaylists: list["subplaylist.SubPlaylist"] = []

        self.FetchObjects()

    def __repr__(self):
        return f'Station("{self.Name}")'

    def __eq__(self, other):
        if other.Name == self.Name: 
            return True

        return False

    def GetName(self):
        return self.Name

    def GetSafeName(self):
        return self.SafeName

    def GetVar(self):
        return "station"
    
    def GetParser(self):
        return self.Parser

    def GetFile(self):
        return self.File

    def GetLuaPath(self) -> str:
        return os.path.join(self.Parser.GetStationsDirectory(), "lua", "cradio", "shared", "stations", self.GetSafeName() + ".lua")

    def GetIcon(self) -> str | None:
        for name in self.DirectoryTree:
            _, fileType = os.path.splitext(name)

            if fileType == ".png":
                return os.path.join(self.Path, name)

        return None
    
    def GetIconPath(self) -> tuple[str, str]:
        ## Filters out dangerous characters before joining our path
        matPath = os.path.join("cradio", "stations", self.GetSafeName() + ".png")
        filePath = os.path.join(self.Parser.GetStationsDirectory(), "materials", matPath)

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
        from entities.song import Song
        from entities.subplaylist import SubPlaylist

        try:
            self.DirectoryTree = os.listdir(self.Path)

            for name in self.DirectoryTree:
                _, fileType = os.path.splitext(name)
                oPath = os.path.join(self.Path, name)
                isFolder = os.path.isdir(oPath)

                if not isFolder and fileType not in validFileTypes:
                    continue

                if isFolder:
                    subPlaylist = SubPlaylist(oPath, self)

                    self.SubPlaylists.append(subPlaylist)
                else:
                    song = Song(oPath, self)

                    self.Songs.append(song)
        except IOError:
            print("Failed to open directory: ", self.Path)

    WriteFormat = '''---------------------------------\n-- Station\n---------------------------------
local station = CRadio:Station("{0}", {{
    {1}
}})

---------------------------------\n-- Songs\n---------------------------------\n'''

    def Write(self):
        ## Gets the list of all music files and folders.
        songs, subPlaylists = self.GetSongs(), self.GetSubPlaylists()

        if not songs and not subPlaylists:
            return False

        name = self.GetName()

        with io.open(self.GetLuaPath(), "w", encoding = "utf-8") as self.File:
            iconPath = self.WriteIcon()
            content = self.WriteFormat.format(
                name,
                f'Icon = "{iconPath}"' if iconPath else ''
            )

            ## We remove empty lines this way.
            content = content.replace('\n    \n', '\n')

            self.File.write(content)

            for song in songs:
                song.Write()

            for subPlaylist in subPlaylists:
                subPlaylist.Write()

    def WriteIcon(self) -> str | None:
        icon = self.GetIcon()

        if not icon:
            return

        destination, matPath = self.GetIconPath()

        shutil.copyfile(icon, destination)

        return matPath