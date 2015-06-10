import rewrite_rules as rr

def remove_id(word):
    return word.count("-") == 0 and word or word[0:word.rindex("-")]
def remove_word(word):
    return word.count("-") == -1 and word or word[(1+word.rindex("-")):]

class DependTree:
    def __init__(self, data, children=[]):
        self.data = remove_id(data) if data is not None else None
        self.children = children
        self.modified = False

    def IsLeaf(self):
        return len(self.children) == 0

    def Print(self,indentation, typ):
        if self.IsLeaf():
            return "(" + (typ + " " if typ != "" else "") + "\"" + str(self.data) + "\")"
        prefix = "(" + (typ + " " if typ != "" else "") + "\"" + str(self.data) + "\" "
        nid = indentation + (" " * len(prefix))
        body = "\n".join([(nid if i > 0  else "") + self.children[i][1].Print(nid,self.children[i][0])
                          for i in xrange(len(self.children))])
        return prefix + body + ")"
    
    def __str__(self):
        return self.Print("","")

    def Find(self,typ, desc=False):
        cands = [i for i,a in enumerate(self.children) if a[0] == typ]
        rr.CHECK(len(cands) != 0)
        return cands[-1 if desc else 0]

    def FindOne(self,typ):
        for t in typ:
            result = self.FindNoCheck(t)
            if not result is None:
                return result
        rr.CHECK(False)

    def FindAll(self, typ):
        return [i for i,a in enumerate(self.children) if a[0] == typ]

    def FindNoCheck(self,typ, desc=False):
        cands = [i for i,a in enumerate(self.children) if a[0] == typ]
        return cands[-1 if desc else 0] if len(cands) != 0 else None

    def CheckAbsense(self,typ):
        cands = [i for i,a in enumerate(self.children) if a[0] == typ]
        rr.CHECK(len(cands) == 0)

    def CheckPrefixAbsense(self,typ):
        cands = [i for i,a in enumerate(self.children) if a[0][:len(typ)] == typ]
        rr.CHECK(len(cands) == 0)

    def CheckOrder(self, t1, t2):
        rr.CHECK(self.Find(t1) < self.Find(t2))

    def FindPrefix(self,typ):
        cands = [i for i,a in enumerate(self.children) if a[0][:len(typ)] == typ]
        rr.CHECK(len(cands) != 0)
        return cands[0]

    def Child(self,i):
        return self.children[i][1]

    def Arc(self,i):
        return self.children[i][0]
    
    def ChildStr(self,i):
        if i == -1:
            return self.data
        return self.Child(i).data

    def Pop(self, i):
        self.modified = True
        self.children.pop(i)
    
    # you can prepend, you can postpend, and their common generalization...?
    #
    def Pend(self, trg, src, pre):
        self.modified = True
        assert trg == -1 or self.Child(trg).IsLeaf()
        assert self.Child(src).IsLeaf()
        c1 = self.ChildStr(src if pre else trg)
        c2 = self.ChildStr(trg if pre else src)
        sep = " " if c1[-1] != "'" and c2[0] != "'" and c2[:3] != "n't" else ""
        # if c2[:2] == "'m" and not c1[-2:].lower() in [" i","i"]:
        #     sep = " "
        #     c2[0] = 'a'
        # if c2[:2] == "'re" and not c1[-4:].lower() in [" you","you"]:
        #     sep = " "
        #     c2[0] = 'a'
        # if c2[:2] == "'s" and c1[-1] == ",":
        #     sep = " "
        #     c2[0] = "i"
        newdata = c1 + sep + c2
        if trg == -1:
            self.data = newdata
        else:
            self.children[trg] = (self.children[trg][0],
                                  DependTree(newdata))
        self.Pop(src)
    
    def Postpend(self, trg, src):
        self.Pend(trg, src, False)

    def Prepend(self, trg, src):
        self.Pend(trg, src, True)

    def Modified(self):
        return self.modified or len([a for a in self.children if a[1].Modified()]) > 0

    def Rewrite(self,rules,depth=0,verbose=False):
        while True:
            for i in xrange(len(self.children)):
                self.Child(i).Rewrite(rules,depth+1,verbose)
            change = False
            for r in rules:
                try:
                    if verbose:
                        strself = self.Print("  "*depth,"")
                    self.modified=False
                    r(self)
                    if verbose:
                        print ("  "*depth) + ("(%s)" % r)
                        print ("  "*depth) + strself
                        print ("  "*depth) + "  --->  " + self.Print("  "*(depth + 4),"")
                    change = True
                    break
                except rr.NoRewriteError as e:
                    assert not self.Modified()
            if not change:
                break
        return self # cause why not

    def ToDict(self):
        return {
            "data" : self.data,
            "children" : [{"arctype" : c1, "child" : c2.ToDict()} for c1,c2 in self.children]
            }


    # Transform in the sense of composable testing
    #
    def Transform(self, arc, target):
        for i in xrange(len(self.children)):
            if self.Arc(i) == arc:
                subrr = FromDependTree(self.Child(i))
                if subrr[0].isupper():
                    target = target[0].upper() + target[1:]
                self.children[i] = (self.Arc(i), DependTree(target))
                return True
        for i in xrange(len(self.children)):
            if self.Child(i).Transform(arc, target):
                return True
        return False
    
def ToDependTree(triplets,root):
    outgoing = [t for t in triplets if t[1] == root]
    children = [(t[0], ToDependTree(triplets, t[2])) for t in outgoing]
    return DependTree(root,children)

def FixPunctuation(sentence):
    puncts = [',',';']
    for p in puncts:
        sentence = sentence.strip(" " + p)
        while True:
            old_sentence = sentence
            sentence = sentence.replace(" " + p, p)
            for q in puncts:
                sentence = sentence.replace(q+p,p)
            if old_sentence == sentence:
                break
    return sentence

def FromDependTree(dt, verbose=False,printres=False):
    if verbose: print "** Structural Pre ***"
    dt.Rewrite(rr.StructuralPreRules,verbose=verbose)
    if verbose: print "*** STRUCTURAL ***"
    dt.Rewrite(rr.StructuralRules,verbose=verbose)
    if verbose: print "*** PRE ***"
    dt.Rewrite(rr.PreRules,verbose=verbose)
    if verbose: print "*** RULES ***"
    dt.Rewrite(rr.Rules,verbose=verbose)
    if printres:
        print dt
    assert dt.IsLeaf(), str(dt)
    return FixPunctuation(dt.data)

def PreProcessDependTree(dt, verbose=False, printres=False):
    dt.Rewrite(rr.StructuralPreRules,verbose=verbose)
    dt.Rewrite(rr.StructuralRules,verbose=verbose)
    return dt

def FlattenDependTree(dt):
    def FDT(dt, result, num):
        for i in xrange(len(dt.children)):
            c = dt.children[i]
            nc = len(result) + 1
            result.append((c[0], dt.data, num, c[1].data, nc))
            FDT(c[1], result, nc)
    result = []
    FDT(dt, result, 0)
    return result
