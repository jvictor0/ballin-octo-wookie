from sentence_builder import Test
import sentence_builder as sb

reload(sb)
reload(sb.rr)
reload(sb.deptree)

transforms = [("dobj","tens of thousands of people"),
              ("nsubj","tens of thousands of people")]

def TestAll(**kwargs):
    Test("dog eats",**kwargs)
    Test("dog eats cat",**kwargs)
    Test("the dog eats the cat",**kwargs)
    Test("the scary dog eats the big cat",**kwargs)
    Test("the scary dog eats the big cat, and the smelly rat",**kwargs)
#    Test("the dog kills and eats the cat",**kwargs)
    Test("the dog is scary",**kwargs)
    Test("the dog will be scary",**kwargs)
    Test("the dog is not scary",**kwargs)
    Test("the dog is not by the barn",**kwargs)
    Test("the dog will not be the president",**kwargs)
    Test("I am the greatest president",**kwargs)
    Test("You shall not pass up this chance to sleep with me",**kwargs)
    Test("You shall not pass up this chance to make out with me",**kwargs)
    Test("Paula handed the keys to her father",**kwargs)
    Test("Paula handed her father the keys",**kwargs)
    Test("The crazy, and cute, dog is not awesome",**kwargs)
    Test("The crazy, but not cute, dog is not awesome",**kwargs)
    Test("The crazy, and not cute, dog is not awesome",**kwargs)
    Test("The not crazy, and not cute, dog is not awesome",**kwargs)
    Test("The not crazy, but cute, dog is not awesome",**kwargs)
    Test("The dog that mother ate is cute",exempt=["dobj"], **kwargs)
    Test("I saw the book which you bought",**kwargs)
    Test("I saw the book which you bought in the attic",**kwargs)
    Test("They shut down the station",**kwargs)
    Test("He purchased it without paying a premium",**kwargs)
    Test("I saw a cat with a telescope",**kwargs)
    Test("All the boys are here",**kwargs)
    Test("The boys, and the girls, are here",**kwargs)
    Test("I love Bill's clothes",**kwargs)
    Test("I love its cool clothes",**kwargs)
    Test("We have no information on whether users are at risk",**kwargs)
    Test("They heard about your missing classes",**kwargs)
    Test("We're annoyed let's face it",**kwargs)
    Test("He says that you like to swim",**kwargs)
    Test("I am certain that he did it",**kwargs)
    Test("I admire the fact that you are honest",**kwargs)
#    Test("What she said is not true",**kwargs)
#    Test("What she said is totally not true",**kwargs)
    Test("She said what is true",**kwargs)
    Test("I ate the cow, and killed the chicken",**kwargs)
    Test("I ate the cow, and didn't kill the chicken",**kwargs)
    Test("I didn't eat the cow, and killed the chicken",**kwargs)
    Test("I didn't eat the cow, or kill the chicken",**kwargs)
    Test("I heard it's a dog",**kwargs)
    Test("Go fuck yourself!") # needs '!' to understand its a command, wont print '!,
    Test("Fuck yourself",**kwargs)
    Test("If I were a cat I would be cute",**kwargs)
    Test("This plan truely helps the middle class",**kwargs)
    Test("Members of both parties have told me so",**kwargs)
    Test("I will send this Congress a budget filled with ideas that are practical in two weeks",**kwargs)
    Test("Each year a tight family should save 15 dollars at the pump",**kwargs)
    Test("Each year a tight family, a freak, should save 15 dollars at the pump",**kwargs)
    Test("I want our actions to tell every child in every neighborhood, your life matters, and we are as committed to improving your life chances, as we are for our own kids",**kwargs)
    Test("I am a really cool cat",**kwargs)
    Test("I quickly ate the dog",**kwargs)
    Test("I am really cool",**kwargs)
    Test("There is a ghost in the room",**kwargs)
    Test("There is no place that does not see you for here",**kwargs)
    Test("There is no place that sees you for here",**kwargs)
#    Test("Yes, passions fly still, but we surely can overcome our differences",**kwargs)
    Test("We're slashing the backlog",**kwargs)
    Test("She looks very beautiful",**kwargs)
    Test("We are as good as ever",**kwargs)
    Test("I want just one",**kwargs)
    Test("I want more than one",**kwargs)
    Test("He cried because of you",**kwargs)
    Test("I have 3.2 billion dollars",**kwargs)
    Test("It's not what keeps us strong",exempt=["nsubj"],**kwargs)
    Test("It isn't what keeps us strong",**kwargs)
    Test("She is working as hard as ever, but has to forego vacations",**kwargs)
    Test("We are any better off",**kwargs)
    Test("It's not like all republicans were sent here to do stuff",exempt=["nsubj"],**kwargs)
    Test("It's not like all republicans were sent here to do what they want",exempt=["dobj","nsubj"],**kwargs)
    Test("The schroeder bank allegedly helped marines recover from acl surgery", **kwargs)
    Test("So eager were they to come that some are said to float over on tree-trunks.", **kwargs)
    Test("So eager were they to come that some are said to have floated over on tree-trunks.", **kwargs)
    Test("So eager were tens of thousands of people to come that some are said to float over on tree-trunks.", **kwargs)
    Test("he changed my life, but would not have liked it", **kwargs)
    Test("I would not have done that", **kwargs)
    Test("Joseph's taste for blood has been well established",**kwargs)
    Test("Joseph's taste for blood was well established",**kwargs)   
    Test("Hundreds, and hundreds, of thousands gathered around the door", **kwargs)
    Test("Tens of thousands of people gathered around the door", **kwargs)
    Test("The Indiana freedom bill is bad", **kwargs)
#    Test("What we are dealing with here is an internationally organized crime syndicate.",**kwargs)
    Test("Since your doctor is going to be asking about your habits ; he should ask, if you are cool",**kwargs)
    Test("To be fair asking a child about your habits would be cruel",**kwargs)
    Test("There is no book that you bought",**kwargs)
#    Test("Huey was however an unknown human potential that they couldn't control", **kwargs)
    
def XCompProblemTest():
    con = sb.database.ConnectToMySQL()
    con.query("use artrat")
    sb.DDL(con, "test")
    sb.Reset(con, "test")
    sb.InsertSentence(con, "test", "Since your doctor is going to be asking about your habits ; he should ask, if you are cool")
    sb.InsertSentence(con, "test", "To be fair asking a child about your habits would be cruel")
    for i in xrange(10):
        print sb.FromDependTree(sb.Generate(con, "test"))
