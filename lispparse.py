

def LispTokenize(str):
    str = str.replace("("," ( ").replace(")"," ) ")
    return str.split()

def LispParse(toks):
    lisp = _LispParse(LispTokenize(toks),0)[0]
    assert len(lisp) == 1
    return lisp[0]

def _LispParse(toks, ix=0):
    result = []
    while ix < len(toks):
        if toks[ix] == "(":
            nxt, ix = _LispParse(toks,ix+1)
            result.append(nxt)
        elif toks[ix] == ")":
            return result, ix+1
        else:
            result.append(toks[ix])
            ix += 1
    return result, ix

def LispPrint(lisp, indentation=""):
    if not isinstance(lisp,list):
        return lisp
    if all([not isinstance(a,list) for a in lisp]):
        return "(" + " ".join(lisp) + ")"
    assert not isinstance(lisp[0], list), "not supporting that..."
    prefix = "(" + lisp[0] + " "
    nid = indentation + (" " * len(prefix))
    body = "\n".join([(nid if i > 1  else "") + LispPrint(lisp[i], nid) for i in xrange(1,len(lisp))])
    return prefix + body + ")"

class Lisp:
    def __init__(self, string = None):
        if string:
            self.l = LispParse(string)

    def __str__(self):
        return LispPrint(self.l)

    def IsLeaf(self):
        return len(self.l) == 2 and not isinstance(self.l[1], list)

    def POS(self):
        return self.l[0]

    def __len__(self):
        return len(self.l) - 1

    def At(self, i):
        result = Lisp()
        result.l = self.l[i+1]
        return result

    def Flatten(self):
        if self.IsLeaf():
            return [tuple(self.l)]
        return [f for i in xrange(len(self)) for f in self.At(i).Flatten()]
