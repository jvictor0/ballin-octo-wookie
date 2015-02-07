import sentence_builder as sb
import database

def Ingest(user, text, **kwargs):
    con = database.ConnectToMySQL()
    return sb.Intest(con, text, user)

def Generate(user, **kwargs):
    con = database.ConnectToMySQL()
    return sb.Generate(user, sb.SubsetSelector):
