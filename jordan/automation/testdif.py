import difflib
import re
import regex
from unidiff import PatchSet # type: ignore
from unidiff.patch import Line, Hunk

# https://docs.python.org/3/library/difflib.html
file1 = open('output.txt', encoding='utf-8')
file2 = open('output2.txt', encoding='utf-8')

diff = difflib.unified_diff(file1.readlines(), file2.readlines(),fromfile=file1.name,tofile=file2.name)
diffs = list(diff)

patch = PatchSet.from_string(''.join(diffs))

class Patch:
    def __init__(self,hunk: Hunk):
        self.value = ''.join([str(i.value) for i in hunk])
        self.added = ''.join([str(i.value) for i in hunk if i.is_added])
        self.removed = ''.join([str(i.value) for i in hunk if i.is_removed])
        self.context = ''.join([str(i.value) for i in hunk])
        self.lineno = hunk.target_start
        self.length = hunk.target_length
        self.source = hunk

hunks = [Patch(j) for i in patch for j in i]

for i in hunks:
    print(regex.sub('(?<=^|\n)', '- ', i.removed.strip()))
    print(regex.sub('(?<=^|\n)', '+ ', i.added.strip()))
    print(i.lineno)
    print()

print(f'{len(patch)} hunks found')
print(f'{len(hunks)} hunks found')
