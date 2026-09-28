import difflib
from unidiff import PatchSet
from unidiff.patch import Line, Hunk

# https://docs.python.org/3/library/difflib.html
file1 = open('output.txt', encoding='utf-8')
file2 = open('output2.txt', encoding='utf-8')

diff = difflib.unified_diff(file1.readlines(), file2.readlines(),fromfile=file1.name,tofile=file2.name)
diffs = list(diff)

patch = PatchSet.from_string(''.join(diffs))

class Patch:
    def __init__(self,hunk: Hunk):
        self.value = '\n'.join([str(i.value) for i in hunk])
        self.added = '\n'.join([str(i.value) for i in hunk if i.is_added])
        self.removed = '\n'.join([str(i.value) for i in hunk if i.is_removed])
        self.lineno = hunk.target_start
        self.length = hunk.target_length
        self.source = hunk

hunks = [Patch(i) for i in patch[0]]

for i in hunks:
    print('\n'.join(["+ "+i.added.rstrip(),"- "+i.removed.rstrip(),str(i.lineno)]))