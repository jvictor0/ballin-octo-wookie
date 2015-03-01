import newspaper as np
from boilerpipe.extract import Extractor
import os.path
import os
from unidecode import unidecode
import public

def Print(x):
    print x

def RefreshArticles(domain, directory, personality, log=Print):
    arts = np.build(domain, language='en', memoize_articles=False).articles
    print domain, "has %d articles" % len(arts)
    for art in arts:
        if not os.path.isfile(directory + "/" + art.url.replace("/","_")):
            art.download()
            log(art.url)
            try:
                extractor = Extractor(extractor='ArticleSentencesExtractor', html=art.html)
            except Exception as e:
                log(e)
                continue
            with open(directory + "/" + art.url.replace("/","_") + "_original","w") as f:
                text = unidecode(extractor.getText())
                print >>f, text
                result = Process(directory, art.url.replace("/","_"), personality, log)
                assert result["success"], result

def Process(directory, filename, personality, log=Print):
    fn = directory + "/" + filename + "_original"
    outfn = directory + "/" + filename + "_processed"
    os.system("cp '%s' '%s'" % (fn, outfn))
    os.system("sed -i 's/\[[0-9]*\]//g' '" + outfn + "'")
    public.IngestFile(personality, outfn)

def Reset(directory, personality, log=Print):
    public.Reset(personality)
    articles = [a[:-len("_original")] for a in os.listdir(directory) if a.endswith("_original")]
    for a in articles:
        Process(directory, a, personality, log)
    
    
