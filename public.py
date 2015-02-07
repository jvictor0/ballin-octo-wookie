import sentence_builder as sb
import database

def Ingest(user, text):
    con = database.ConnectToMySQL()
    con.query("use sentencebuilder")
    sb.DDL(con, user)
    try:
        sb.Ingest(con, text, user)
        return { "success": True }
    except Exception as e:  # Complain if nessesary
        return { "success": False, "error": str(e) }

def Generate(user):
    con = database.ConnectToMySQL()
    con.query("use sentencebuilder")
    dbs = {}
    try:
        gend = sb.Generate(con, user, sb.SubsetSelector)
        result = sb.FromDependTree(gend)
        dbs = sb.g_last_generated.ToDict()
        return { "success": True, "body": result,   "debugging_stuff" : { "original_tree" : dbs } }
    except Exception as e:
        return { "success": False, "error": str(e), "debugging_stuff" : { "original_tree" : dbs } }

def Reset(user):
    con = database.ConnectToMySQL()
    con.query("use sentencebuilder")
    sb.Reset(con, user)
    return { "success": True }
