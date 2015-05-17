import depend_tree as deptree

def CHECK(a):
    if not a:
        raise NoRewriteError()

class NoRewriteError:
    def __init__(self):
        pass

def PrepRW(t):
    for i in xrange(len(t.children)):
        if not "_" in t.children[i][0]:
            continue
        tp = t.children[i][0].split("_")[0]
        if tp in ["prep","prepc","rcmod"]:
            CHECK(t.Child(i).IsLeaf())
            neg = False
            if tp == "prep":
                try:
                    neg = t.Find("neg")
                    CHECK(t.Child(neg).IsLeaf())
                    t.data = t.data + " " + t.ChildStr(neg)
                except NoRewriteError as e:
                    neg = False
            t.data = t.data + " " + t.children[i][0].split("_")[1]
            t.Postpend(-1, i)
            if neg != False:
                neg = t.Find("neg")
                t.Pop(neg)
            return t
    CHECK(False)

def ConjRW(t):
    for i in xrange(len(t.children)):
        if t.children[i][0].split("_")[0]  == "conj":
            CHECK(t.Child(i).IsLeaf())
            if t.children[i][0] == "conj_negcc":
                conj = ", but not"
            else:
                conj = ", " + t.children[i][0].split("_")[1]
            t.data = t.data + " " + conj
            t.children[i][1].data = t.ChildStr(i) + ","
            t.Postpend(-1, i)
            return t
    CHECK(False)

def CompSentRW(t):
    nsubj = t.Find("nsubj")
    dobj  = t.Find("dobj")
    ccomp = t.Find("ccomp")

    CHECK(t.Child(nsubj).IsLeaf())
    CHECK(t.Child(dobj ).IsLeaf())
    CHECK(t.Child(ccomp).IsLeaf())
    
    t.Prepend(-1, nsubj)
    t.Prepend(-1, t.Find("dobj"))
    t.Postpend(-1, t.Find("ccomp"))
    return t
    
def RCModRW(t):
    rcm = t.FindOne(["rcmod"])
    rcmobj = t.Child(rcm).Find("dobj")
    t.Child(rcm).CheckOrder("dobj","nsubj")
    CHECK(t.Child(rcm).Child(rcmobj).IsLeaf())
    t.children[rcm] = ("rcmod_" + t.Child(rcm).ChildStr(rcmobj),t.children[rcm][1])
    t.Child(rcm).Pop(rcmobj)
    return t

def XCompCCompObjRW(t):
    xcomp = t.Find("xcomp")
    ccomp = t.Child(xcomp).Find("ccomp")
    dobj  = t.Child(xcomp).Child(ccomp).Find("dobj")
#    t.Child(xcomp).Child(ccomp).CheckAbsense("aux")
    CHECK(t.Child(xcomp).Child(ccomp).Child(dobj).IsLeaf())
    children = t.Child(xcomp).Child(ccomp).children
    children[dobj] = ("mark",children[dobj][1])
    t.modified = True
    return t

def AdvmodAmodFn(auxpass):
    def AdvmodAmod(t):
        amod = t.FindOne(["amod","acomp","advmod","ccomp"])
        advmod = t.Child(amod).Find("advmod")
        if auxpass:
            t.Child(amod).Find("auxpass")
        CHECK(t.Child(amod).Child(advmod).IsLeaf())
        t.Child(amod).Pend(-1, advmod, t.children[amod][0] not in ["ccomp"])
        t.modified = True
        return t
    return AdvmodAmod

def AuxAposRW(t):
    aux = t.Find("aux")
    CHECK(t.ChildStr(aux)[0] == "'")
    CHECK(t.Child(aux).IsLeaf())
    t.Prepend(-1, aux)
    return t
        
def NegAuxRW(t):
    neg = t.Find("neg")
    aux = t.FindOne(["aux"])
    CHECK(t.Child(neg).IsLeaf())
    CHECK(t.Child(aux).IsLeaf())
    t.Postpend(aux, neg)
    return t

def QuantmodDepRW(t):
    quantmod = t.Find("quantmod")
    dep = t.Find("dep")
    CHECK(t.Child(quantmod).IsLeaf())
    CHECK(t.Child(dep).IsLeaf())
    t.Prepend(quantmod, dep)
    return t
    t.Prepend(-1, t.Find("dep"))

def NegCCompRW(t):
    neg = t.Find("neg")
    aux = t.Find("ccomp")
    CHECK(t.Child(neg).IsLeaf())
    CHECK(t.Child(aux).IsLeaf())
    t.Prepend(aux, neg)
    return t

def RootRW(t):
    CHECK(t.data == "ROOT")
    CHECK(len(t.children) == 1)
    CHECK(t.Child(0).IsLeaf())
    CHECK(t.children[0][0] == "root")
    t.data = t.ChildStr(0)
    t.children = []

def AdvmodAsObjRW(t):
    advmod = t.Find("advmod")
    t.CheckAbsense("dobj")
    t.CheckAbsense("cop")
    t.CheckAbsense("ccomp")
    t.CheckAbsense("dep")
    CHECK(t.Child(advmod).IsLeaf())
    t.Postpend(-1, advmod)
    return t

def AdvmodPassiveRW(t):
    advmod = t.Find("advmod")
    pas = t.FindOne(["nsubjpass"])
    CHECK(t.Child(advmod).IsLeaf())
    t.Prepend(-1, advmod)
    return t

def AdvmodCSubjRW(t):
    advmod = t.Find("advmod")
    csubj = t.FindOne(["csubj"])
    CHECK(t.Child(advmod).IsLeaf())
    CHECK(t.Child(csubj).IsLeaf())
    t.Prepend(csubj, advmod)
    return t

def PossRW(t):
    l = t.Find("poss")
    CHECK(t.Child(l).IsLeaf())
    if not t.ChildStr(l).lower() in ["his","her","my","their","your","our","its"]:
        t.children[l][1].data = t.ChildStr(l) + "'s"
    t.Pend(-1, l, True)
    return t

def MultiAuxRW(t):
    auxs = t.FindAll("aux")
    CHECK(len(auxs) > 1)
    for a in auxs:
        CHECK(t.Child(a).IsLeaf())
    negs = t.FindAll("neg")
    for a in negs:
        CHECK(t.Child(a).IsLeaf())
    auxstext = [t.ChildStr(a) for a in auxs + negs]
    ordr = ["to","would","not","_","have"]
    auxstext.sort(key = lambda itm : ordr.index(itm if itm in ordr else "_"))
    for i in xrange(len(auxs)):
        t.Pop(t.FindNoCheck("aux"))
    for i in xrange(len(negs)):
        t.Pop(t.FindNoCheck("neg"))
    assert t.FindNoCheck("aux") is None
    assert t.FindNoCheck("neg") is None
    t.children.append(("aux",deptree.DependTree(" ".join(auxstext))))
    return t

def ExplSubjRW(t):
    expl = t.Find("expl")
    return br("nsubj", False)(t)
    
def br(typ, pre, prefix=None,suffix=None, desc=False, requiring=[], requiring_absense=[]):
    def f(t):
        l = t.Find(typ, desc=desc)
        for r in requiring:
            t.Find(r)
        for r in requiring_absense:
            t.CheckAbsense(r)
        CHECK(t.Child(l).IsLeaf())
        if not prefix is None:
            t.children[l][1].data = prefix + t.ChildStr(l)
        if not suffix is None:
            t.children[l][1].data = t.ChildStr(l) + suffix
        t.Pend(-1, l, pre)
        return t
    return f

StructuralPreRules = [
    AdvmodAmodFn(True)
    ]

StructuralRules = [
    MultiAuxRW,
    NegAuxRW,
    NegCCompRW,
    AuxAposRW,
    
    AdvmodAmodFn(True),
    br("advmod",True,requiring=["auxpass","nsubjpass"]),
    br("advmod",False,requiring=["auxpass"], requiring_absense=["dobj","cop","ccomp","dep"]),
    br("advmod",True,requiring=["auxpass"]),

    br("det",True,requiring=["aux"]),
    br("neg",True,requiring=["aux"]),
    br("cop",True,requiring=["aux"]),


    br("auxpass", True),
    br("aux", True),

    ]
PreRules = [
    RCModRW,
    AdvmodAmodFn(False),
    XCompCCompObjRW,
    ]
Rules = [
    RootRW,
    MultiAuxRW,
    NegAuxRW,
    NegCCompRW,
    AuxAposRW,
    br("nn", True, desc=True),
    br("amod", True, desc=True),
    br("num", True),
    AdvmodCSubjRW,
    AdvmodPassiveRW,
    AdvmodAsObjRW,
    br("advmod", True),
    QuantmodDepRW,
    br("quantmod",True),
    br("det", True),
    br("predet", True),
    br("prt", False),
    br("pcomp",False),
    PossRW,
    br("dep",False),
#    CompSentRW,
    br("iobj",False),
    br("dobj",False),
    br("vmod", False),
    br("acomp", False),
    ConjRW,
    br("preconj",True),
    ExplSubjRW,
    br("ccomp",False),
    br("rcmod",False),
    PrepRW,
    br("pobj",False),
    br("neg", True),
    br("cop",True),
    br("auxpass", True),
    br("aux", True),
    br("xcomp", False),
    br("nsubj",True),
    br("nsubjpass",True),
    br("csubj",True),
    br("expl",True),
    br("prep",False),
    br("tmod", True),
    br("mwe",True),
    br("number",True),
    br("mark",True),
    br("advcl",False,prefix=", ",suffix=","),
    br("appos",False,prefix=", ",suffix=","),
    br("parataxis",False,prefix="; ",suffix=","),
    br("discourse",True,prefix=", ",suffix=","),
    ]
