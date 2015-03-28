import random
import nltk.data
import copy
import client
import corenlp
import time
from unidecode import unidecode


# select group_id, agg(data)
# from t outer_t
# where exists
#     (select * from t inner_t where inner_t.data = "specific data" and inner_t.data = outer_t.group_d)
# group by group_id

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
    "arc_wildness" : ARC_WILDNESS
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
        self.data = remove_id(data)
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

    def Find(self,typ):
        cands = [i for i,a in enumerate(self.children) if a[0] == typ]
        CHECK(len(cands) != 0)
        return cands[0]

    def FindOne(self,typ):
        for t in typ:
            result = self.FindNoCheck(t)
            if not result is None:
                return result
        CHECK(False)

    def FindAll(self, typ):
        return [i for i,a in enumerate(self.children) if a[0] == typ]

    def FindNoCheck(self,typ):
        cands = [i for i,a in enumerate(self.children) if a[0] == typ]
        return cands[0] if len(cands) != 0 else None

    def CheckAbsense(self,typ):
        cands = [i for i,a in enumerate(self.children) if a[0] == typ]
        CHECK(len(cands) == 0)

    def FindPrefix(self,typ):
        cands = [i for i,a in enumerate(self.children) if a[0][:len(typ)] == typ]
        CHECK(len(cands) != 0)
        return cands[0]

    def Child(self,i):
        return self.children[i][1]
    
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
                        print ("  "*depth) + strself
                        print ("  "*depth) + "  --->  " + self.Print("  "*(depth + 4),"")
                    change = True
                    break
                except NoRewriteError as e:
                    assert not self.modified
            if not change:
                break
        return self # cause why not

    def ToDict(self):
        return {
            "data" : self.data,
            "children" : [{"arctype" : c1, "child" : c2.ToDict()} for c1,c2 in self.children]
            }
    
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
    t.Child(rcm).CheckAbsense("aux")
    CHECK(t.Child(rcm).Child(rcmobj).IsLeaf())
    t.children[rcm] = ("rcmod_" + t.Child(rcm).ChildStr(rcmobj),t.children[rcm][1])
    t.Child(rcm).Pop(rcmobj)
    return t

def XCompCCompObjRW(t):
    xcomp = t.Find("xcomp")
    ccomp = t.Child(xcomp).Find("ccomp")
    dobj  = t.Child(xcomp).Child(ccomp).Find("dobj")
    t.Child(xcomp).Child(ccomp).CheckAbsense("aux")
    CHECK(t.Child(xcomp).Child(ccomp).Child(dobj).IsLeaf())
    children = t.Child(xcomp).Child(ccomp).children
    children[dobj] = ("mark",children[dobj][1])
    t.modified = True
    return t

def AdvmodAmod(t):
    amod = t.FindOne(["amod","acomp","advmod","ccomp"])
    advmod = t.Child(amod).Find("advmod")
    CHECK(t.Child(amod).Child(advmod).IsLeaf())
    t.Child(amod).Pend(-1, advmod, t.children[amod][0] not in ["ccomp"])
    t.modified = True
    return t

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
    csubj = t.Find("csubj")
    CHECK(t.Child(advmod).IsLeaf())
    CHECK(t.Child(csubj).IsLeaf())
    t.Prepend(csubj, advmod)
    return t

def PossRW(t):
    l = t.Find("poss")
    CHECK(t.Child(l).IsLeaf())
    if not t.ChildStr(l) in ["his","her","my","their","your","our","its"]:
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
    
def br(typ, pre, prefix=None,suffix=None):
    def f(t):
        l = t.Find(typ)
        CHECK(t.Child(l).IsLeaf())
        if not prefix is None:
            t.children[l][1].data = prefix + t.ChildStr(l)
        if not suffix is None:
            t.children[l][1].data = t.ChildStr(l) + suffix
        t.Pend(-1, l, pre)
        return t
    return f

PreRules = [
    RCModRW,
    AdvmodAmod,
    XCompCCompObjRW,
    ]
Rules = [
    RootRW,
    MultiAuxRW,
    NegAuxRW,
    NegCCompRW,
    AuxAposRW,
    br("nn", True),
    br("amod", True),
    br("num", True),
    AdvmodCSubjRW,
    AdvmodPassiveRW,
    AdvmodAsObjRW,
    br("advmod", True),
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
    br("quantmod",True),
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
    br("parataxis",False,prefix=", ",suffix=","),
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
    dt.Rewrite(PreRules,verbose=verbose)
    dt.Rewrite(Rules,verbose=verbose)
    if printres:
        print dt
    assert dt.IsLeaf(), str(dt)
    return FixPunctuation(dt.data)
    
    
def Test(sentence, verbose=False):
    print sentence
    global NLP
    InitNLP()
    dt = ToDependTree(NLP.parse(sentence)["sentences"][0]["dependencies"],"ROOT-0")
    print dt
    result = FromDependTree(dt,verbose=verbose,printres=True)
    assert result == sentence.strip(".").strip("!"), "\n%s\n%s" % (result,sentence)
    print

def TestAll(verbose=False):
    Test("dog eats",verbose=verbose)
    Test("dog eats cat",verbose=verbose)
    Test("the dog eats the cat",verbose=verbose)
    Test("the scary dog eats the big cat",verbose=verbose)
    Test("the scary dog eats the big cat, and the smelly rat",verbose=verbose)
#    Test("the dog kills and eats the cat",verbose=verbose)
    Test("the dog is scary",verbose=verbose)
    Test("the dog will be scary",verbose=verbose)
    Test("the dog is not scary",verbose=verbose)
    Test("the dog is not by the barn",verbose=verbose)
    Test("the dog will not be the president",verbose=verbose)
    Test("I am the greatest president",verbose=verbose)
    Test("You shall not pass up this chance to sleep with me",verbose=verbose)
    Test("You shall not pass up this chance to make out with me",verbose=verbose)
    Test("Paula handed the keys to her father",verbose=verbose)
    Test("Paula handed her father the keys",verbose=verbose)
    Test("The crazy, and cute, dog is not awesome",verbose=verbose)
    Test("The crazy, but not cute, dog is not awesome",verbose=verbose)
    Test("The crazy, and not cute, dog is not awesome",verbose=verbose)
    Test("The not crazy, and not cute, dog is not awesome",verbose=verbose)
    Test("The not crazy, but cute, dog is not awesome",verbose=verbose)
    Test("The dog that mother ate is cute",verbose=verbose)
    Test("I saw the book which you bought",verbose=verbose)
    Test("I saw the book which you bought in the attic",verbose=verbose)
    Test("They shut down the station",verbose=verbose)
    Test("He purchased it without paying a premium",verbose=verbose)
    Test("I saw a cat with a telescope",verbose=verbose)
    Test("All the boys are here",verbose=verbose)
    Test("The boys, and the girls, are here",verbose=verbose)
    Test("I love Bill's clothes",verbose=verbose)
    Test("I love its cool clothes",verbose=verbose)
    Test("We have no information on whether users are at risk",verbose=verbose)
    Test("They heard about your missing classes",verbose=verbose)
    Test("We're annoyed let's face it",verbose=verbose)
    Test("He says that you like to swim",verbose=verbose)
    Test("I am certain that he did it",verbose=verbose)
    Test("I admire the fact that you are honest",verbose=verbose)
#    Test("What she said is not true",verbose=verbose)
#    Test("What she said is totally not true",verbose=verbose)
    Test("She said what is true",verbose=verbose)
    Test("I ate the cow, and killed the chicken",verbose=verbose)
    Test("I ate the cow, and didn't kill the chicken",verbose=verbose)
    Test("I didn't eat the cow, and killed the chicken",verbose=verbose)
    Test("I didn't eat the cow, or kill the chicken",verbose=verbose)
    Test("I heard it's a dog",verbose=verbose)
    Test("Go fuck yourself!") # needs '!' to understand its a command, wont print '!,
    Test("Fuck yourself",verbose=verbose)
    Test("If I were a cat I would be cute",verbose=verbose)
    Test("This plan truely helps the middle class",verbose=verbose)
    Test("Members of both parties have told me so",verbose=verbose)
    Test("I will send this Congress a budget filled with ideas that are practical in two weeks",verbose=verbose)
    Test("Each year a tight family should save 15 dollars at the pump",verbose=verbose)
    Test("Each year a tight family, a freak, should save 15 dollars at the pump",verbose=verbose)
    Test("I want our actions to tell every child in every neighborhood, your life matters, and we are as committed to improving your life chances, as we are for our own kids",verbose=verbose)
    Test("I am a really cool cat",verbose=verbose)
    Test("I quickly ate the dog",verbose=verbose)
    Test("I am really cool",verbose=verbose)
    Test("There is a ghost in the room",verbose=verbose)
    Test("There is no place that does not see you for here",verbose=verbose)
    Test("Yes, passions fly still, but we can surely overcome our differences",verbose=verbose)
    Test("We're slashing the backlog",verbose=verbose)
    Test("She looks very beautiful",verbose=verbose)
    Test("We are as good as ever",verbose=verbose)
    Test("I want just one",verbose=verbose)
    Test("I want more than one",verbose=verbose)
    Test("He cried because of you",verbose=verbose)
    Test("I have 3.2 billion dollars",verbose=verbose)
    Test("It's not what keeps us strong",verbose=verbose)
    Test("It isn't what keeps us strong",verbose=verbose)
    Test("She is working as hard as ever, but has to forego vacations",verbose=verbose)
    Test("We are any better off",verbose=verbose)
    Test("It's not like all republicans were sent here to do stuff",verbose=verbose)
    Test("It's not like all republicans were sent here to do what they want",verbose=verbose)
    Test("the schroeder bank allegedly helped marines recover from acl surgery", verbose=verbose)
    Test("So eager were they to come that some are said to float over on tree-trunks.", verbose=verbose)
    Test("So eager were they to come that some are said to have floated over on tree-trunks.", verbose=verbose)
    Test("he changed my life, but would not have liked it", verbose=verbose)
    Test("I would not have done that", verbose=verbose)
    Test("Joseph's taste for blood has been well established",verbose=verbose)

    
def Reset(con, user):
    con.query("drop table %s_dependencies" % user)
    con.query("drop table %s_sentences" % user)
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


def InsertSentence(con, user, sentence):
    # if you SQL inject me I'll urinate on you
    sentence = sentence.encode("utf8")
    global NLP
    print sentence
    if nlp_parsed is None:
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
                break

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
    ProcessDependencies(con, user, result["sentences"], filename, log=log)

def RandomWeightedChoice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c,w  in choices:
        if upto + w > r:
            return c
        upto += w
    assert False, choices

# This can be optimized a few ways:
#    1) If we arent adding new data, the subselect without the where or group by could be materialized and given a key(dependant, dependant_id, arctype, sentence_id) or something
#    2) Not doing the join at all since we only use it to fill in the nulls for leaf nodes and get the grandparent arctype.
#        both of these things could be added to the original table for only increase in rowcount and columnsize
#        Then the only key we'd need is the one mentioned above
def HistogramSubsets(con, word, parent_arctype = None, fixed_arc= None, fixed_word = None, user = None, **kwargs):
    subs =  ("select dl.sentence_id as sid, dl.dependant_id as did, group_concat(dr.arctype separator ',') as gc "
             "from %s_dependencies dl left join %s_dependencies dr "
             "on dl.sentence_id = dr.sentence_id and dl.dependant_id = dr.governor_id "
             "where dl.dependant = %%s %s "
             "group by dl.sentence_id, dl.dependant_id ")
    extra_cond = ""
    params = [word]
    if not fixed_arc is None:
        assert not fixed_word is None
        print "fixed", fixed_word, fixed_arc, word, parent_arctype
        extra_cond = ("and ('%s',%%s) in (select arctype, dependant from %s_dependencies where "
                      "sentence_id = dl.sentence_id and governor_id = dl.dependant_id) ")
        extra_cond = extra_cond % (fixed_arc, user)
        params.append(fixed_word)
    if not parent_arctype is None:
        extra_cond += ("and dl.arctype = '%s'" % parent_arctype)
    subs = subs % (user, user, extra_cond)
    q = subs
    hists = [([] if r["gc"] is None else r["gc"].split(","),r["sid"],r["did"]) for r in con.query(q, *params)]
    disallowed = ["cc"]
    if len(hists) == 0:
        assert False,  "before filtering no rows"
    hists = [h for h in hists if len([x for x in h[0] if x in disallowed]) == 0]
    hists = [h for h in hists if len([x for x in h[0] if x == "nsubj"]) < 2] # i simple cant even
    return hists

def SubsetSelector(con, word, fixed_arc=None, fixed_word = None,height=0, user=None, params = None, **kwargs):
    if params is None:
        params = DEFAULT_PARAMS
    hist = HistogramSubsets(con, word, user=user, fixed_arc = fixed_arc, fixed_word = fixed_word, **kwargs)
    if not fixed_arc is None:
        for h in hist:
            assert fixed_arc in h[0]
    if len(hist) == 0:
        assert False,  "generated no rows"
        return []
    for i in xrange(len(hist)):
        denom = 1.0 if height == 0 else (params["height_throttler"] * float(height))**len(hist[i][0])
        hist[i] = (hist[i], 1.0/denom)
    result_entry = RandomWeightedChoice(hist)
    q = "select * from %s_dependencies where sentence_id = %s and governor_id = %s" % (user, result_entry[1], result_entry[2])
    print con.query("select sentence from %s_sentences where id = %s" % (user, result_entry[1]))[0]["sentence"]
    result = [(r["arctype"], r["dependant"]) for r in con.query(q)]
    if not fixed_arc is None:
        result.pop(result.index((fixed_arc, fixed_word)))
    for i in xrange(len(result)):
        if result[i][0] in params["arc_wildness"] and random.random() < params["arc_wildness"][result[i][0]]:
            next_word = RandomDependant(con, user, word, result[i][0])
            print "   (%s) %s -> %s" % (result[i][0], result[i][1], next_word)
            result[i] = (result[i][0], next_word)
    return result

def RandomDependant(con, user, gov, arctype):
    q = "select dependant from %s_dependencies where governor = %%s and arctype = %%s" % user
    return random.choice(con.query(q,gov,arctype))['dependant']
        
def Expand(con, word, height=0, user=None, fixed_chain = None, **kwargs):
    if not fixed_chain is None and len(fixed_chain) == 0:
        fixed_chain = None
    arctypes = SubsetSelector(con, word, user=user, height = height, 
                              fixed_arc  = fixed_chain[0][0] if not fixed_chain is None else None,
                              fixed_word = fixed_chain[0][1] if not fixed_chain is None else None, **kwargs)
    outs = []
    for at,dep in arctypes:
        outs.append((at,Expand(con, dep,
                               height = height + 1, user=user, fixed_chain=None, parent_arctype=at)))
    if not fixed_chain is None:
        outs.append((fixed_chain[0][0],
                     Expand(con, fixed_chain[0][1],
                            height = height + 1, user=user,
                            fixed_chain=fixed_chain[1:], parent_arctype=fixed_chain[0][0])))
    return DependTree(word,outs)

# SeekToRoot :: dependant -> [(arctype, dependant)]
def SeekToRoot(con, user, dependant):
    result = []
    q = (("select governor, arctype from %s_dependencies "
          "where dependant = %%s"))
    q = q % user
    rows = con.query(q,dependant.encode("utf8"))
    if len(rows) == 0:
        return []
    row = random.choice(rows)
    result.append((row["arctype"],dependant))
    dependant = row['governor']
    while dependant != 'root':
        q = (("select sentence_id as sid, governor_id as gid from %s_dependencies "
              "where arctype = '%s' and governor = %%s and dependant = %%s"))
        q = q % (user, result[-1][0])
        rows = con.query(q, dependant, result[-1][1])
        assert len(rows) != 0
        row = random.choice(rows)
        rows = con.query("select governor, arctype from %s_dependencies where sentence_id = %s and dependant_id = %s" % (user, row["sid"], row["gid"]))
        assert len(rows) == 1, rows
        result.append((rows[0]['arctype'], dependant))
        dependant = rows[0]['governor']
    return result[-1::-1]

g_last_generated = None

def Generate(con, user, using=None):
    if not using is None:
        fixed_chain = SeekToRoot(con, user, using)
        if len(fixed_chain) == 0:
            return None
        print fixed_chain
        word = fixed_chain[0][1]
        fixed_chain.pop(0)
    else:
        fixed_chain = None
        word = random.choice(con.query("select dependant from %s_dependencies where arctype = 'root'" % user))['dependant']
    global g_last_generated
    result = Expand(con, word, parent_arctype='root', user=user, fixed_chain=fixed_chain)
    g_last_generated = copy.deepcopy(result)
    return result

def GenerateAndExpand(con, user, using=None):
    result = FromDependTree(Generate(con, user, using=using))
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
            

