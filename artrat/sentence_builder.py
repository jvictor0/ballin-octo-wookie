import random
import nltk.data
import copy
import client
import corenlp
import time
from unidecode import unidecode
import database


HEIGHT_THROTTLER = 1.0
ARC_WILDNESS = {
    "amod" : 0.5,
    "num" : 0.5,
    "iobj" : 0.5,
    "dobj" : 0.5,
    "vmod" : 0.5,
    "rcmod" : 0.2,
    "pobj" : 0.5,
    "quantmod" : 0.5,
    "nsubj" : 0.5,
    "nsubjpass" : 0.5,
    "csubj" : 0.25,
    "number" : 0.5
    }
DEFAULT_PARAMS = {
    "height_throttler" : HEIGHT_THROTTLER,
    #    "arc_wildness" : ARC_WILDNESS
    "arc_wildness" : { }
    }


NLP = None
def InitNLP():
    global NLP
    if NLP is None:
        NLP = client.StanfordNLP()

def Print(x):
    print x

def remove_id(word):
    return word.count("-") == 0 and word or word[0:word.rindex("-")]
def remove_word(word):
    return word.count("-") == -1 and word or word[(1+word.rindex("-")):]

class NoRewriteError:
    def __init__(self):
        pass

class DependTree:
    def __init__(self, data, children=[]):
        self.data = remove_id(data) if data is not None else None
        self.children = children
        self.modified = False

    def IsLeaf(self):
        return len(self.children) == 0

    def Print(self,indentation, typ):
        if self.IsLeaf():
            return "(" + (typ + " " if typ != "" else "") + "\"" + self.data + "\")"
        prefix = "(" + (typ + " " if typ != "" else "") + "\"" + self.data + "\" "
        nid = indentation + (" " * len(prefix))
        body = "\n".join([(nid if i > 0  else "") + self.children[i][1].Print(nid,self.children[i][0])
                          for i in xrange(len(self.children))])
        return prefix + body + ")"
    
    def __str__(self):
        return self.Print("","")

    def Find(self,typ, desc=False):
        cands = [i for i,a in enumerate(self.children) if a[0] == typ]
        CHECK(len(cands) != 0)
        return cands[-1 if desc else 0]

    def FindOne(self,typ):
        for t in typ:
            result = self.FindNoCheck(t)
            if not result is None:
                return result
        CHECK(False)

    def FindAll(self, typ):
        return [i for i,a in enumerate(self.children) if a[0] == typ]

    def FindNoCheck(self,typ, desc=False):
        cands = [i for i,a in enumerate(self.children) if a[0] == typ]
        return cands[-1 if desc else 0] if len(cands) != 0 else None

    def CheckAbsense(self,typ):
        cands = [i for i,a in enumerate(self.children) if a[0] == typ]
        CHECK(len(cands) == 0)

    def CheckPrefixAbsense(self,typ):
        cands = [i for i,a in enumerate(self.children) if a[0][:len(typ)] == typ]
        CHECK(len(cands) == 0)

    def CheckOrder(self, t1, t2):
        CHECK(self.Find(t1) < self.Find(t2))

    def FindPrefix(self,typ):
        cands = [i for i,a in enumerate(self.children) if a[0][:len(typ)] == typ]
        CHECK(len(cands) != 0)
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
                except NoRewriteError as e:
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
    
def CHECK(a):
    if not a:
        raise NoRewriteError()

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
    t.children.append(("aux",DependTree(" ".join(auxstext))))
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
    br("ccomp",False),
    br("rcmod",False),
    PrepRW,
    br("pobj",False),
    br("neg", True),
    br("cop",True),
    br("auxpass", True),
    br("aux", True),
    br("xcomp", False),
    ExplSubjRW,
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

def ToDependTree(triplets,root):
    outgoing = [t for t in triplets if t[1] == root]
    children = [(t[0], ToDependTree(triplets, t[2])) for t in outgoing]
    return DependTree(root,children)

def FixPunctuation(sentence):
    sentence = sentence.strip(" ,")
    while True:
        old_sentence = sentence
        sentence = sentence.replace(" ,",",")
        sentence = sentence.replace(",,",",")
        if old_sentence == sentence:
            break
    return sentence

def FromDependTree(dt, verbose=False,printres=False):
    dt.Rewrite(StructuralPreRules,verbose=verbose)
    dt.Rewrite(StructuralRules,verbose=verbose)
    dt.Rewrite(PreRules,verbose=verbose)
    dt.Rewrite(Rules,verbose=verbose)
    if printres:
        print dt
    assert dt.IsLeaf(), str(dt)
    return FixPunctuation(dt.data)

def PreProcessDependTree(dt, verbose=False, printres=False):
    dt.Rewrite(StructuralPreRules,verbose=verbose)
    dt.Rewrite(StructuralRules,verbose=verbose)
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
    
def Test(sentence, verbose=False, transforms=[], exempt=[]):
    print sentence
    global NLP
    InitNLP()
    dt = ToDependTree(NLP.parse(sentence)["sentences"][0]["dependencies"],"ROOT-0")
    print dt
    result = FromDependTree(copy.deepcopy(dt),verbose=verbose,printres=True)
    assert result == sentence.strip(".").strip("!"), "\n%s\n%s" % (result,sentence)
    for arc,tg in transforms:
        if arc in exempt:
            continue
        dtcopy = copy.deepcopy(dt)
        if dtcopy.Transform(arc,tg):            
            result = FromDependTree(dtcopy,verbose=verbose,printres=False)
            Test(result, verbose=verbose)
    print

def Reset(con, user):
    con.query("drop table %s_dependencies" % user)
    con.query("drop table %s_sentences" % user)
    con.query("drop table %s_procd" % user)
    DDL(con,user)

def DDL(con, user):
    con.query("create database if not exists artrat")
    con.query("use artrat")
    con.query(("create table if not exists %s_dependencies"
               "(sentence_id bigint"
               ",arctype varchar(255) charset utf8mb4 not null"
               ",governor varchar(255) charset utf8mb4  not null"
               ",dependant varchar(255) charset utf8mb4  not null"
               ",governor_id int not null"
               ",dependant_id int not null"
               ",primary key(sentence_id,dependant_id)"
               ",key(governor, governor_id)" 
               ",key(dependant, dependant_id)"
               ")") % user)
    con.query(("create table if not exists %s_sentences"
               "(id bigint primary key auto_increment"
               ",sentence text charset utf8mb4"
               ",source text default null)") % user)
    con.query("create table if not exists %s_procd like %s_dependencies" % (user,user))

def UpdateProcd(con, user):
    con.query("drop table %s_procd" % user)
    DDL(con, user)
    ids = [int(r["id"]) for r in con.query("select id from %s_sentences" % user)]
    for i in xrange(len(ids)):
        if i % 100 == 0:
            print "%f%% done" % (100*float(i)/len(ids))
        ix = ids[i]
        PostProcessSentence(con, ix, user)

def PostProcessSentence(con, i, user):
    procd = FlattenDependTree(PreProcessDependTree(SentenceIdDependTree(user,i, con)))
    if len(procd) == 0:
        return
    q = "insert into %s_procd values" % user
    params = []
    for p in procd:
        q += "(%d, '%s', %%s, %%s, %d, %d)," % (i, p[0], p[2], p[4])
        params.append(p[1])
        params.append(p[3])
    q = q.strip(",")
    try:
        con.query(q, *params)
    except Exception as e:
        print q
        print params
        print i
        raise e
    
def InsertSentence(con, user, sentence):
    # if you SQL inject me I'll urinate on you
    sentence = sentence.encode("utf8")
    global NLP
    print sentence
    if NLP is None:
        InitNLP()
    nlp_parsed = NLP.parse(sentence.decode("utf8").encode("ascii","ignore"))
    depsa = nlp_parsed["sentences"]
    ProcessDependencies(con, user, depsa)
def ProcessDependencies(con, user, depsa, source=None, log=Print):
    for deps in depsa:
        txt = deps["text"].encode("utf8")
        try:
            if source is None:
                sid = str(con.execute("insert into %s_sentences(sentence) values(%%s)" % (user), txt))
            else:
                sid = str(con.execute("insert into %s_sentences(sentence,source) values(%%s,%%s)" % (user), txt, unidecode(source)))
            log("inserting (%s), sentence_id = %s" % (user,sid))
        except Exception as e:
            log("insert sentence error " + str(e))
            continue
        deps = deps["dependencies"]
        failed = False
        for at, gv, dp in deps:
            values = [sid, "'%s'" % at, "%s",  "%s", remove_word(gv), remove_word(dp)]
            q = "insert into %s_dependencies values (%s)" % (user,",".join(values))
            try:
                con.query(q.encode("utf8"),
                          remove_id(gv).lower().encode("utf8"),
                          remove_id(dp).lower().encode("utf8"))
            except Exception as e:
                log("insert dep error " + str(e))
                con.query("delete from %s_sentences where id = %s" % (user,sid))
                con.query("delete from %s_dependencies where sentence_id = %s" % (user,sid))
                failed = True
                break
        if not failed:            
            PostProcessSentence(con, int(sid), user)

            
def GetSymbols(text):
    global NLP
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    texts = tokenizer.tokenize(text.decode("utf8"))
    result = {}
    for sentence in texts:
        sentence = sentence.encode("utf8")
        InitNLP()
        depsa = NLP.parse(sentence.decode("utf8").encode("ascii","ignore"))["sentences"]
        for deps in depsa:
            dt = ToDependTree(deps["dependencies"],"ROOT-0")
            next_result = GetImportantWords(dt, deps)
            for k,v in next_result.iteritems():
                if not k in result:
                    result[k] = 0
                result[k] += v
    return result

def Ingest(con, text, user):
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    texts = tokenizer.tokenize(text.decode("utf8"))
    for sentence in texts:
        InsertSentence(con, user, sentence)

def IngestFile(con, filename, user, log=Print):
    result = corenlp.ParseAndSaveFile(filename)
    con.query("begin")
    try:        
        ProcessDependencies(con, user, result["sentences"], filename, log=log)
        con.query("commit")
    except Exception:
        con.query("rollback")
        raise

def RandomWeightedChoice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c,w  in choices:
        if upto + w > r:
            return c
        upto += w
    assert False, choices

def Subset(superset,subset):
    for elem in set(subset):
        if superset.count(elem) < subset.count(elem):
            return False
    return True

# this function find a all sentences containing a given word under a given arctype
# for each fixed sibling, the toplevel arctype will be present.
# the return type is [([(arctype, word)], sentence_id, dependant_id)]
# 
def HistogramSubsets(con, word, parent_arctype = None, fixed_siblings=DependTree(None), user = None, **kwargs):
    subs =  ("select dl.sentence_id as sid, dl.dependant_id as did, "
             "group_concat(dr.arctype separator ',')   as gc_arc, "
             "group_concat(dr.dependant separator ',') as gc_dep "
             "from %s_procd dl left join %s_procd dr "
             "on dl.sentence_id = dr.sentence_id and dl.dependant_id = dr.governor_id "
             "where dl.dependant = %%s %s "
             "group by dl.sentence_id, dl.dependant_id ")
    extra_cond = ""
    params = [word]
    if not parent_arctype is None:
        extra_cond += ("and dl.arctype = '%s'" % parent_arctype)
    subs = subs % (user, user, extra_cond)
    q = subs
    hists = [( ([] if r["gc_arc"] is None else r["gc_arc"].split(",")),
               ([] if r["gc_dep"] is None else r["gc_dep"].split(",")),
               r["sid"],
               r["did"]) 
             for r in con.query(q, *params)]
    disallowed = ["cc"]
    disallowed.extend(["num","number"]) # this will add some stability for now...
    if len(hists) == 0:
        assert False,  "before filtering no rows"
    result = []
    assert fixed_siblings.data is None
    fixed_tups = [(fs[0], fs[1].data) for fs in fixed_siblings.children if False]
    for h in hists:
        assert len(h[0]) == len(h[1])
        if len([x for x in h[0] if x in disallowed]) == 0 and len([x for x in h[0] if x == "nsubj"]) < 2:
            zipd = zip(h[0],h[1])
            if Subset(zipd, fixed_tups):
                result.append((zipd, h[2], h[3]))
    return result

# returns [(arctype, word, fixed_arcs)]
def SubsetSelector(con, word, fixed_siblings=DependTree(None), height=0, user=None, params = None, dbg_out={}, **kwargs):
    if params is None:
        params = DEFAULT_PARAMS
    hist = HistogramSubsets(con, word, user=user, fixed_siblings=fixed_siblings, **kwargs)
    if len(hist) == 0:
        assert False,  "generated no rows, word = %s, \nfixed=%s" % (word, str(fixed_siblings))
        return []
    for i in xrange(len(hist)):
        denom = float(len(hist[i][0])) if height == 0 else (params["height_throttler"] * float(height))**len(hist[i][0])
        hist[i] = (hist[i], 0 if denom == 0 else (1.0/denom))
    result_entry = RandomWeightedChoice(hist)
    q = "select * from %s_procd where sentence_id = %s and governor_id = %s" % (user, result_entry[1], result_entry[2])
    result = [(r["arctype"], r["dependant"], r["dependant_id"]) for r in con.query(q)]
    assert [(a,b) for a,b,c in result] == result_entry[0], (result,result_entry)

    if "used_list" not in dbg_out:
        dbg_out["used_list"] = []
    if len(result) != 0:
        dbg_out["used_list"].append(int(result_entry[1]))

    fixed_ixs = set([])
    for at,fs in fixed_siblings.children:
        found = False
        for i in xrange(len(result)):
            if (result[i][0],result[i][1]) == (at,fs.data):
                fixed_ixs.add(i)
                result[i] = (at, fs.data, DependTree(None, fs.children))
                found = True
                break
        assert found, (at,fs.data,result)
    for i in xrange(len(result)):
        if i not in fixed_ixs:
            fixd = DependTree(None)
            result[i] = (result[i][0], result[i][1], fixd)
        
    for i in xrange(len(result)):
        if result[i][0] in params["arc_wildness"] and random.random() < params["arc_wildness"][result[i][0]]:
            next_word = RandomDependant(con, user, word, result[i][0])
            print "   (%s) %s -> %s" % (result[i][0], result[i][1], next_word)
            result[i] = (result[i][0], next_word, result[i][2])
    return result

def GetDependants(con, user, sentence_id, gov_id):
    q = "select arctype, dependant from %s_procd where governor_id = %%s and sentence_id = %%s" % user
    return [(a["arctype"], a["dependant"]) for a in con.query(q,gov_id, sentence_id)]


def RandomDependant(con, user, gov, arctype):
    q = "select dependant from %s_procd where governor = %%s and arctype = %%s" % user
    return random.choice(con.query(q,gov,arctype))['dependant']
        
def Expand(con, word, height=0, user=None, fixed_siblings = DependTree(None), dbg_out = {}, **kwargs):
    arctypes = SubsetSelector(con, word, user=user, height = height, 
                              fixed_siblings = fixed_siblings, 
                              dbg_out = dbg_out, **kwargs)
    outs = []
    for at,dep,fixd in arctypes:
        outs.append((at,Expand(con, dep,
                               height = height + 1, user=user, fixed_siblings=fixd, parent_arctype=at, dbg_out=dbg_out)))
    return DependTree(word,outs)

# SeekToRoot :: dependant -> fixed_tree
def SeekToRoot(con, user, dependant):
    result = []
    q = (("select governor, arctype from %s_procd "
          "where dependant = %%s"))
    q = q % user
    rows = con.query(q,dependant.encode("utf8"))
    if len(rows) == 0:
        return DependTree(None)
    row = random.choice(rows)
    result.append((row["arctype"],dependant))
    dependant = row['governor']
    while dependant != 'root':
        q = (("select sentence_id as sid, governor_id as gid from %s_procd "
              "where arctype = '%s' and governor = %%s and dependant = %%s"))
        q = q % (user, result[-1][0])
        rows = con.query(q, dependant, result[-1][1])
        assert len(rows) != 0
        row = random.choice(rows)
        rows = con.query("select governor, arctype from %s_procd where sentence_id = %s and dependant_id = %s" % (user, row["sid"], row["gid"]))
        assert len(rows) == 1, rows
        result.append((rows[0]['arctype'], dependant))
        dependant = rows[0]['governor']
        result_tree = []
    for at, dep in result:
        result_tree = [(at, DependTree(dep, result_tree))]
    assert result_tree[0][0] == 'root', result_tree
    return result_tree[0][1]

g_last_generated = None

def Generate(con, user, using=None, dbg_out={}):
    if not using is None:
        fixed_chain = SeekToRoot(con, user, using)
        if fixed_chain.data is None:
            return None
        word = fixed_chain.data
    else:
        fixed_chain = DependTree(None)
        word = random.choice(con.query("select dependant from %s_procd where arctype = 'root'" % user))['dependant']
    global g_last_generated
    result = Expand(con, word, parent_arctype='root', user=user, fixed_chain=fixed_chain,dbg_out=dbg_out)
    g_last_generated = copy.deepcopy(result)
    return result

def GenerateAndExpand(user, using=None):
    con = database.ConnectToMySQL()
    con.query("use artrat")
    dbg_out = { "used_list" : [] }
    result = FromDependTree(Generate(con, user, using=using,dbg_out=dbg_out))
    print "sentences_used" , dbg_out["used_list"]
    print g_last_generated
    return result

def GenerateWithSymbols(con, user, symbols):
    symbols = { k.encode("utf8") : v for k,v in symbols.iteritems() }
    while len(symbols) != 0:
        using = RandomWeightedChoice(symbols.items())
        del symbols[using]
        result = Generate(con, user, using)
        if not result is None:
            syms = GetImportantWords(DependTree("root", [("root",result)]), { "words" : []})
            return result, syms
    result = Generate(con, user, None)
    syms = GetImportantWords(DependTree("root", [("root",result)]), { "words" : []})
    return result, syms
    
def SentenceIdDependTree(user,sid, con):
    rows = con.query("select arctype, governor, dependant, governor_id, dependant_id from %s_dependencies where sentence_id = %d" % (user,sid))
    deps = [(r["arctype"], r['governor'] + "-" + r['governor_id'], r['dependant'] + "-" + r['dependant_id']) for r in rows]
    return ToDependTree(deps, root='root-0')


def PrintSentences(user,sids):
    for s in sids:
        PrintSentence(user,s)


def PrintSentence(user,sid):
    con = database.ConnectToMySQL()
    con.query("use artrat")
    print con.query("select * from %s_sentences where id = %d" % (user,sid))[0]['sentence']
    print SentenceIdDependTree(user,sid, con)

def GetImportantWords(parsetree, nlp):
    root = parsetree.Child(parsetree.Find("root"))
    result = { root.data : 1 }
    nsubj = root.FindNoCheck("nsubj")
    if not nsubj is None:
        if not root.ChildStr(nsubj) in result:
            result[root.ChildStr(nsubj)] = 0
        result[root.ChildStr(nsubj)]+= 3
    dobj = root.FindNoCheck("dobj")
    if not dobj is None:
        if not root.ChildStr(dobj) in result:
            result[root.ChildStr(dobj)] = 0
        result[root.ChildStr(dobj)]+= 3
    for w,mw in nlp["words"]:
        if mw["NamedEntityTag"] != 'O':
            if not w in result:
                result[w] = 0
            result[w]+= 10
    return result
            

if __name__ == "__main__":
    TestAll()
