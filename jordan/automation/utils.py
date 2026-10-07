import re


def flatten(v) :
    """
    Compresses a matrix into an arrray
    """
    return [
        x
        for xs in v
        for x in xs
    ]

 
def printList(v):
    """
    Prints an array.
    """
    if type(v) is dict:
        l = max([len(key) for key in v])
        for i, j in v.items(): print(i.ljust(l),'\t' ,j)
    else:
        for i in v: print(i)

def searchList(rule: str, v: list, matchNotMach = True):
    """
    Returns items in a list that match a RegEx rule.
    
    Parameters
    ----------
    rule : str
        The RegEx rule
    v : list
        The list
    matchNotMatch = True
        Whether the item should match the rule or not match the rule
    """
    return [o for o in v if bool(re.search(rule,o)) ^ (not matchNotMach)]

def index(v: list):
    """
    Prints the list numbered
    """
    for i in range(len(v)):
        print(str(i) + "\t" + str(v[i]))
    

def goIndex(v):
    """
    Asks for an index in a list, or a number item in a dict
    """
    if len(v) == 0:
        raise IndexError('Sequence is empty')
    print('Enter number:')
    if type(v) is dict:
        i = 0
        for key, val in v.items():
            print(str(i) + "\t[" + key + "]=" + val)
            i+=1
        return list(v.keys())[int(input())]
    else:
        for i in range(len(v)):
            print(str(i) + "\t" + str(v[i]))
        return v[int(input("> "))]
    
print('Imported extensions')
print("(C) 2024, 2026 Jordan Ferrazza")