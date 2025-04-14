import os
from parser import Parser

cParser: Parser | None = None

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

def main():
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

if __name__ == "__main__":
    main()