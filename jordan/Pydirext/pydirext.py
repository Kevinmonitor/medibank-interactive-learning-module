from genericpath import *
import os
from pathlib import Path
import re
import errno
import string
import subprocess
import time
from types import NoneType
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from utils import *


class Pydirext:

    #https://stackoverflow.com/questions/827371/is-there-a-way-to-list-all-the-available-windows-drives
    @staticmethod
    def available_drives():
        """
        Returns the path of all logical drives in the system.
        """
        return ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]

    def __init__(self, path = "."):
        self._here = "."
        self.here = path
    
    @property
    def here(self):
        """
        Sets and gets the object's chosen directory. Change with 'here' or 'cd(...)' (Both use relative paths to the current path!).

        """
        return self._here
    
    @here.setter
    def here(self, v):
        """
        Changes directory.
        
        Raises
        ------
        FileNotFoundError
            New directory does not exist.
        NotADirectoryError
            New directory is not a directory.
        """
        x = self.abspath(v)
        print("Changing directory of " + str(self) + " from " + self.here + " to " + x)
        if not isfile(x) and not isdir(x): raise FileNotFoundError
        if not isdir(x): raise NotADirectoryError
        self._here = x

    def cd(self, v):
        """
        Changes directory then returns the new path.

        Raises
        ------
        FileNotFoundError
            New directory does not exist.
        NotADirectoryError
            New directory is not a directory.
        """
        self.here = v
        return self.here
    
    @property
    def ld(self):
        """
        Returns a list of folder items in the path 'here'.
        """
        return [self.join(x) for x in os.listdir(self.here)]

    def peek(self, v):
        """
        Returns a list of folder items of another folder relative to the path 'here', instead of from 'here'.
        """
        return [self.abspath(os.path.join(v,x)) for x in os.listdir(self.join(v))]

    def relpath(self, v):
        """
        Returns a relative path relative to the path 'here'. Similar to 'os.path.relpath' but uses 'here' as the start path.

        For example, peekrelpath("C:/foo/bar/baz") at "bar" returns "baz".
        """
        return os.path.relpath(v,self.here)
    
    def peekrelpath(self, path, v):
        """
        Returns a relative path relative to another path which is relative to the path 'here' (similar to 'peek()'). Similar to 'os.path.relpath' but uses '[here]\\\\[path]' as a start path.
        
        For example, peekrelpath("..","C:/foo/bar/baz") at "bar" returns "bar\\baz".
        """
        return os.path.relpath(v,self.join(path))
    
    def join(self , *v):
        """
        Joins a relative path to the path 'here'. Similar to 'os.path.join' but uses 'here' as a starting point.
        
        For example, join("bar") at "C:/foo" returns "C:/foo/bar".

        """
        return os.path.join(self.here, *v)
    
    def abspath(self, v):
        """
        Generates an absolute path relative to path 'here', instead of the working directory.

        For example,
            abspath("bar") at "foo" in "C:/foo/bar/baz" returns "C:/foo/bar", not "C:/foo/bar/baz/bar".
            abspath("..") at "foo" in "C:/foo/bar/baz" returns "C:/", not "C:/foo/bar/".
        """
        return os.path.abspath(self.join(v))

get = None
if __name__ == '__main__':
    get = Pydirext()


def navigate(dir = get):
    """
        Browse for a directory using pydirext object 'dir'
    """

    while True:
        print("Enter a number or text:")
        print("(0 to finish, Ctrl+Z to abort)")
        j = 0
        li = [None, dir.abspath("..") ] + dir.ld[:]
        for i in li:
            if i == None:
                print ("0. " + dir.here)
            else:
                print(str(j) + ".\t [" + ("D" if isdir(i) else "F") + "]" + dir.relpath(i))
            j=j+1
        choice = ''
        result = ''
        search = []
        good = False
        while not good:
            choice = input()
            if choice.isdigit():
                if int(choice) >= len(li):
                    print("Invalid index")
                    print("Try again")
                else:
                    good = True
            else:
                search = [i for i in li if i != None and (choice.lower() in dir.relpath(i).lower())]
                if len(search) == 0:
                    print("Option not found")
                    print("Try again")
                elif len(search) != 1:
                    print("Ambiguous option")
                    for k, l in enumerate(li):
                        if (l in search):
                            print("\t" + str(k) + ".\t" + dir.relpath(l))
                    print("Try again (all items)")
                else:
                    good = True
        if not choice.isdigit():
            result = search[0]
        else:
            result = li[int(choice)]
        if result == None: return dir.here
        elif not isdir(result):
            start(['explorer',result])
            return result
        else:
            dir.cd(result)
        print("==============================")
    

def filesIn(paths : list):
    """
    Returns a list of files from the list of paths. (Does not open folders)
    """
    return [o for o in paths if isfile(o)]

def dirsIn(paths : list):
    """
    Returns a list of folders from the list of paths. (Does not open folders)
    """
    return [o for o in paths if isdir(o)]

def subsIn(paths : list):
    """
    Returns a list of sub-files and subfolders in a list of folders. Skips files. (Opens folders)
    """
    return flatten([[os.path.join(y,x) for x in os.listdir(y)] for y in paths if isdir(y)])

def subsIn2(paths : list):
    """
    Returns a list of files, folders, sub-files and subfolders in a list of folders. (Both does and does not folders)
    """
    return  flatten([[y]+ [os.path.join(y,x) for x in os.listdir(y)] for y in paths if isdir(y)])

def namesIn(paths : list):
    """
    Returns filenames from a list of paths.
    """
    return [re.split('\\\\(?=[^\\\\]+$)',o)[-1] for o in paths]

def pathsIn(paths : list):
    """
    Returns file paths from a list of paths.
    """
    return [re.split('\\\\(?=[^\\\\]+$)',o)[:-1] for o in paths]

def dirOrFileIn(paths : list):
    """
    Returns whether a path is a file or a folder in a list of paths.
    """
    return dict(zip(paths,["D" if isdir(o) else "F" for o in paths]))

def start(*args: list):
    if len(args) == 1:
        args = ['explorer'] + list(args[0:])
    print(str.join(' ', args))
    subprocess.Popen(args)
    time.sleep(1)

def start2(*args: list):
    if len(args) == 1:
        args = list(args[0:])
    print(str.join(' ', args))
    subprocess.Popen(args)
    time.sleep(1)

print('Imported Pydirext and its objects')
print("(C) 2024 Jordan Ferrazza")
