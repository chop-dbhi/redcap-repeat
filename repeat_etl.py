import os
import csv
import redcap_repeat
from pyparsing import *

key = redcap_repeat.key

class RepeatETL(object):
    
    def __init__(self, filename):
        handle_in = open(filename, 'rU')
        input_f = csv.reader(handle_in)

        self.cells = []
        for line in input_f:
            self.cells.extend([row[0] for row in \
                redcap_repeat.dispatch[line[key['d']]](line)])

        # Skip header
        self.cells=";".join(self.cells[1:])+";"

    def starting(self):
        print 'starting'
    def ending(self):
        print 'ending'
    def oneline(self):
        print 'just line'
    def single(self):
      print 'singlerepeat'
    
    def printTape(self):
        print self.cells


    def getGrammar(self):
        group = Forward()
        begin = Keyword("startrepeat")
        end = Keyword("endrepeat")
        single = Keyword("repeat")
        
        startline = Word(alphanums+"${}_/")+begin+Word(alphanums+'[_${}]')+Group(OneOrMore(Word(alphas+"/_()")))+Literal(';')
        singlerepeat = Word(alphanums+"${}_")+single+Word(alphanums+'[_${}]')+Group(OneOrMore(Word(alphas+"/+()")))+Literal(';')
        line = Word(alphanums+"${}_").leaveWhitespace()+Literal(';')
        endline = Optional(Word(alphanums+"${}_").leaveWhitespace())+end+Literal(';')
        
        startline.setParseAction(self.starting)
        endline.setParseAction(self.ending)
        line.setParseAction(self.oneline)
        singlerepeat.setParseAction(self.single)
       
        group << startline + ZeroOrMore(line | singlerepeat | group) + endline
        return OneOrMore(line | group | singlerepeat)



    def getSchema(self):
     
       return self.getGrammar().parseString(self.cells)
