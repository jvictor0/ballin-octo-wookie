import client


class PTDB:
    def __init__(self):
        self.db = { }

    def Get(self, pos):
        if pos in self.db:
            return random.choice(self.db[pos])
        return None

    def Insert(self, pos, lisp):
        if not pos in self.db:
            self.db[pos] = []
        self.db[pos].append(lisp)

    def InsertLisp(self, lisp):
        self.Insert(lisp.POS(), lisp)
        if lisp.IsLeaf():
            return
        for i in xrange(len(lisp)):
            self.InsertLisp(lisp.At(i))

def InsertMany(tweets):
    nlp = client.StanfordNLP()
    result = PTDB()
    for t in tweets:
        res = nlp.parse(t)
        for s in res["sentences"]:
            result.InsertLisp(s["parsetree"])
    return result
        
