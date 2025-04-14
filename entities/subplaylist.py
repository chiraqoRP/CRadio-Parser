import os
import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import entities.station as station
    import entities.song as song

def SanitizeName(str):
    ## Filters out spaces
    str = re.sub(r'[^\w]', '_', str)

    ## Additionally filters out non-ASCII characters, as source doesn't like them.
    return re.sub(r'[^\x00-\x7F]+', '', str).lower()

validFileTypes = [".mp3", ".ogg", ".flac"]

class SubPlaylist:
    def __init__(self, path: str, parent: "station.Station"):
        self.Path = path
        self.Name = os.path.basename(path)
        self.SafeName = SanitizeName(self.Name)

        self.Parent = parent
        self.Songs: list["song.Song"] = []

        self.FetchSongs()

    def __repr__(self):
        return f'SubPlaylist("{self.Parent.GetName()}" - "{self.GetName()}")'

    def __eq__(self, other): 
        if other.Name == self.Name:
            return True

        return False

    def GetName(self) -> str:
        return self.Name

    def GetSafeName(self) -> str:
        return self.SafeName
    
    def GetParent(self):
        return self.Parent
    
    def GetStation(self):
        return self.Parent
    
    def GetVar(self) -> str:
        return self.GetSafeName() + "Playlist"

    def GetSongs(self):
        return self.Songs
    
    def FetchSongs(self):
        from entities.song import Song

        try:
            self.DirectoryTree = os.listdir(self.Path)

            for name in self.DirectoryTree:
                _, fileType = os.path.splitext(name)
                oPath = os.path.join(self.Path, name)

                ## We don't want to include sub-playlists.
                if os.path.isdir(oPath) or fileType not in validFileTypes:
                    continue

                song = Song(oPath, self)

                self.Songs.append(song)
        except IOError:
            print("Failed to open directory: ", self.Path)

        return self.Songs

    InfoLine = "\n---------------------------------\n-- {0} (Playlist)\n---------------------------------\n"
    MainFormat = 'local {0} = CRadio:SubPlaylist("{1}")\n'
    ParentFormat = '{0}:SetParent(station)\n\n'
    WriteFormat = '''---------------------------------------------\n-- {1} (Playlist)\n---------------------------------------------\n
local {0} = CRadio:SubPlaylist("{1}", {{
    Parent = {2}
}})\n\n'''

    def Write(self):
        stationFile = self.GetStation().GetFile()
        stationFile.write(self.WriteFormat.format(
            self.GetVar(),
            self.GetName(),
            self.GetStation().GetVar()
        ))

        for song in self.GetSongs():
            song.Write()