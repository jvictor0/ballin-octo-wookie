import twitter
import time

api = twitter.Api(
    consumer_key="vTv5DoifFBbU2TBlDV18gj2Tf",
    consumer_secret="dgw5BuBgI4mMR7lJC8bWtY2zza6QZr03TjNAfxpMORxPsgGOoL",
    access_token_key="3012615866-CRm9RgXImzeIW77AbcbU97Ob26R9JPaxZ3M1pBm",
    access_token_secret="sV3gOmAjrkm4DaRl8Ik1CSrtEY65IN0UpGqeKyieDlu7Y")

last = 564140570986041344

while True:
    rep = api.GetSearch("to:bottymouth", since_id=last)
    for r in rep:
        print "blah"
        api.PostUpdates("@" + r.GetUser().screen_name + " get at me")
        last = r.id
    time.sleep(30) 

