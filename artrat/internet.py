import client as c
import urllib2
import html2text
import nltk.data

def ReadWebsite(url):
    html = urllib2.urlopen(url).read().decode("utf8")
    text = html2text.html2text(html)
   
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    texts = tokenizer.tokenize(text)
    text = ""
    nlp = c.StanfordNLP()
    results = []
    count = 0
    for t in texts:
        count += 1
        print float(count)/float(len(texts))
        try:
            psd = nlp.parse(t)["sentences"]
        except Exception as e:
            print e
            nlp = c.StanfordNLP()
            continue
        print "parsed"
        for s in psd:
            results.append(s["dependencies"])
    return results
        
    
