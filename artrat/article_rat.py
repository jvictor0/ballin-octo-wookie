import newspaper as np
from boilerpipe.extract import Extractor
import os.path
import os, time, random
from unidecode import unidecode
import public
import hashlib
from subprocess import call

def Print(x):
    print x

def ArticleRat(directory, the_personalities, log=Print):
    while True:
        t0 = time.time()
        random.shuffle(the_personalities)
        for p, d in the_personalities:
            RefreshArticles(d, os.path.join(directory,p), p, log=log, timeout=60*60)
        time.sleep(t0 - 12 * 60 * 60) # dont refresh the same article in 12 hours

def RefreshArticles(domain, directory, personality, log=Print, timeout=None):
    start_time = time.time()
    arts = np.build(domain, language='en', memoize_articles=False).articles
    log(domain + " has %d articles" % len(arts))
    for art in arts:
        if not timeout is None and time.time() - start_time > timeout:
            log("Timeout after %f secons" % (time.time() - start_time))
            return
        DownloadAndProcess(url, directory, personality, log=log)
        
def DownloadAndProcess(url, directory, personality, log=Print):
    art = np.Article(url)
    hashd_fn = hashlib.sha256(unidecode(art.url)).hexdigest()
    base_fn = directory + "/" + hashd_fn
    orig_fn = base_fn + "_original"
    if not os.path.isfile(orig_fn):
        try:
            art.download()
            log(art.url)
            extractor = Extractor(extractor='ArticleSentencesExtractor', html=art.html)
        except Exception as e:
            log(str(e))
            return
        with open(orig_fn,"w") as f:
            text = unidecode(extractor.getText())
            print >>f, text
        result = Process(directory, hashd_fn, personality, log=log)
        assert result["success"], result

def VirginProcess(directory, filename, personality, log=Print):
    fn = directory + "/" + filename
    call("mv '%s' '%s'" % (fn, fn + "_original"), shell=True)
    Process(directory, filename, personality, log=log)

def Process(directory, filename, personality, log=Print):
    fn = directory + "/" + filename + "_original"
    outfn = directory + "/" + filename + "_processed"
    call("cp '%s' '%s'" % (fn, outfn), shell=True)
    call("sed -i 's/\[[0-9]*\]//g' '" + outfn + "'", shell=True)
    return public.IngestFile(personality, outfn, log=log)

def Reset(directory, personality, log=Print):
    public.Reset(personality)
    articles = [a[:-len("_original")] for a in os.listdir(directory) if a.endswith("_original")]
    for a in articles:
        Process(directory, a, personality, log=log)
    
    
