import newspaper as np
from boilerpipe.extract import Extractor
import os.path, os.system
from unidecode import unidecode
import sentencebuilder

def RefreshArticles(domain, directory, personality, format_fn=lambda x:x):
    arts = np.build(domain, language='en', memoize_articles=False).articles
    print domain, "has %d articles" % len(arts)
    for art in arts:
        if not os.path.isfile(directory + "/" + art.url.replace("/","_")):
            art.download()
            print art.url
            try:
                extractor = Extractor(extractor='ArticleSentencesExtractor', html=art.html)
            except Exception as e:
                print e
                continue
            with open(directory + "/" + art.url.replace("/","_") + "_original","w") as f:
                text = unidecode(extractor.getText())
                print >>f, text
                Process(directory, art.url.replace("/","_"), personality)

def Process(directory, filename, personality):
    fn = directory + "/" + filename + "_original"
    outfn = directory + "/" + filename + "_processed"
    os.system("cp %s %s" % (fn, outfn))
    os.system("sed -i 's/\[[0-9]*\]//g' " + outfn)
    sentencebuilder.IngestFile(outfn)
