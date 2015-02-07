import sentence_builder as sb
import database

def Ingest(user, text, **kwargs):
    con = database.ConnectToMySQL()
    con.query("use sentencebuilder")
    sb.DDL(con, user)
    try:
        sb.Ingest(con, text, user)
        return { "success": True }
    except Exception as e:  # Complain if nessesary
        return { "success": False, "error": str(e) }

def Generate(user, **kwargs):
    con = database.ConnectToMySQL()
    con.query("use sentencebuilder")
    try:
        gend = sb.Generate(con, user, sb.SubsetSelector)
        result = sb.FromDependTree(gend)
        return { "success": True, "body": result }
    except Exception as e:
        return { "success": False, "error": str(e) }

def Reset(user):
    con = database.ConnectToMySQL()
    con.query("use sentencebuilder")
    sb.Reset(con, user)
    return { "success": True }
