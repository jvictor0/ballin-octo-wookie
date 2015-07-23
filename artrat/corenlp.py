#!/usr/bin/env python
#
# corenlp  - Python interface to Stanford Core NLP tools
# Copyright (c) 2014 Dustin Smith
#   https://github.com/dasmith/stanford-corenlp-python
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import json
import optparse
import os, re, sys, time, traceback
import jsonrpc, pexpect
from progressbar import ProgressBar, Fraction
import logging
import unidecode
from subprocess import call

VERBOSE = False

STATE_START, STATE_TEXT, STATE_WORDS, STATE_TREE, STATE_DEPENDENCY, STATE_COREFERENCE = 0, 1, 2, 3, 4, 5
WORD_PATTERN = re.compile('\[([^\]]+)\]')
CR_PATTERN = re.compile(r"\((\d*),(\d)*,\[(\d*),(\d*)\]\) -> \((\d*),(\d)*,\[(\d*),(\d*)\]\), that is: \"(.*)\" -> \"(.*)\"")

# initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

jars = ["stanford-corenlp-3.5.1.jar",
        "stanford-corenlp-3.5.1-models.jar",
        "joda-time.jar",
        "xom.jar",
        "jollyday.jar"]

# if CoreNLP libraries are in a different directory,
# change the corenlp_path variable to point to them
abs_prefix = os.path.dirname(__file__)
corenlp_path = os.path.join(abs_prefix,"stanford-corenlp-full-2015-01-29/")
    
java_path = "java"
classname = "edu.stanford.nlp.pipeline.StanfordCoreNLP"
# include the properties file, so you can change defaults
# but any changes in output format will break parse_parser_results()
props = "-props %s" % os.path.join(abs_prefix,"default.properties")

# add and check classpaths
jars = [corenlp_path + jar for jar in jars]
for jar in jars:
    if not os.path.exists(jar):
        logger.error("Error! Cannot locate %s" % jar)
        assert False
        
# spawn the server
start_corenlp = "%s -Xmx1800m -cp %s %s %s" % (java_path, ':'.join(jars), classname, props)



def remove_id(word):
    return word
    """Removes the numeric suffix from the parsed recognized words: e.g. 'word-2' > 'word' """
    return word.count("-") == 0 and word or word[0:word.rindex("-")]


def parse_bracketed(s):
    '''Parse word features [abc=... def = ...]
    Also manages to parse out features that have XML within them
    '''
    word = None
    attrs = {}
    temp = {}
    # Substitute XML tags, to replace them later
    for i, tag in enumerate(re.findall(r"(<[^<>]+>.*<\/[^<>]+>)", s)):
        temp["^^^%d^^^" % i] = tag
        s = s.replace(tag, "^^^%d^^^" % i)
    # Load key-value pairs, substituting as necessary
    for attr, val in re.findall(r"([^=\s]*)=([^=\s]*)", s):
        if val in temp:
            val = temp[val]
        if attr == 'Text':
            word = val
        else:
            attrs[attr] = val
    return (word, attrs)


def parse_parser_results(text):
    #print text
    """ This is the nasty bit of code to interact with the command-line
    interface of the CoreNLP tools.  Takes a string of the parser results
    and then returns a Python list of dictionaries, one for each parsed
    sentence.
    """
    results = {"sentences": []}
    state = STATE_START
    for line in text.encode('utf-8').split("\n"):
        line = line.strip()
        
        if line.startswith("Sentence #"):
            sentence = {'words':[], 'parsetree':[], 'dependencies':[]}
            results["sentences"].append(sentence)
            state = STATE_TEXT
        
        elif state == STATE_TEXT:
            sentence['text'] = line
            state = STATE_WORDS
        
        elif state == STATE_WORDS:
            if not line.startswith("[Text="):
                raise Exception('Parse error. Could not find "[Text=" in: %s' % line)
            for s in WORD_PATTERN.findall(line):
                sentence['words'].append(parse_bracketed(s))
            state = STATE_TREE
        
        elif state == STATE_TREE:
            if len(line) == 0:
                state = STATE_DEPENDENCY
                sentence['parsetree'] = " ".join(sentence['parsetree'])
            else:
                sentence['parsetree'].append(line)
        
        elif state == STATE_DEPENDENCY:
            if len(line) == 0:
                state = STATE_COREFERENCE
            else:
                split_entry = re.split("\(|, ", line[:-1])
                if len(split_entry) == 3:
                    rel, left, right = map(lambda x: remove_id(x), split_entry)
                    sentence['dependencies'].append(tuple([rel,left,right]))
        
        elif state == STATE_COREFERENCE:
            if "Coreference set" in line:
                if 'coref' not in results:
                    results['coref'] = []
                coref_set = []
                results['coref'].append(coref_set)
            else:
                for src_i, src_pos, src_l, src_r, sink_i, sink_pos, sink_l, sink_r, src_word, sink_word in CR_PATTERN.findall(line):
                    src_i, src_pos, src_l, src_r = int(src_i)-1, int(src_pos)-1, int(src_l)-1, int(src_r)-1
                    sink_i, sink_pos, sink_l, sink_r = int(sink_i)-1, int(sink_pos)-1, int(sink_l)-1, int(sink_r)-1
                    coref_set.append(((src_word, src_i, src_pos, src_l, src_r), (sink_word, sink_i, sink_pos, sink_l, sink_r)))
    
    return results


class StanfordCoreNLP(object):
    """
    Command-line interaction with Stanford's CoreNLP java utilities.
    Can be run as a JSON-RPC server or imported as a module.
    """
    def __init__(self):
        """
        Checks the location of the jar files.
        Spawns the server as a process.
        """
        print start_corenlp
        if VERBOSE: 
            logger.info(start_corenlp)
        self.corenlp = pexpect.spawn(start_corenlp)
        
        # show progress bar while loading the models
        widgets = ['Loading Models: ', Fraction()]
        pbar = ProgressBar(widgets=widgets, maxval=5, force_update=True).start()
        self.corenlp.expect("done.", timeout=20) # Load pos tagger model (~5sec)
        pbar.update(1)
        self.corenlp.expect("done.", timeout=200) # Load NER-all classifier (~33sec)
        pbar.update(2)
        self.corenlp.expect("done.", timeout=600) # Load NER-muc classifier (~60sec)
        pbar.update(3)
        self.corenlp.expect("done.", timeout=600) # Load CoNLL classifier (~50sec)
        pbar.update(4)
        self.corenlp.expect("done.", timeout=200) # Loading PCFG (~3sec)
        pbar.update(5)
        self.corenlp.expect("Entering interactive shell.")
        pbar.finish()
    
    def _parse(self, text):
        """
        This is the core interaction with the parser.
        
        It returns a Python data-structure, while the parse()
        function returns a JSON object
        """
        # clean up anything leftover
        while True:
            try:
                left = self.corenlp.read_nonblocking (4000, 0.3)
            except pexpect.TIMEOUT:
                break

        while len(text) != 0:
            amount = self.corenlp.send(text)
            text = text[amount:]
        self.corenlp.sendline("")
        # How much time should we give the parser to parse it?
        # the idea here is that you increase the timeout as a 
        # function of the text's length.
        # anything longer than 5 seconds requires that you also
        # increase timeout=5 in jsonrpc.py
        max_expected_time = min(40, 3 + len(text) / 20.0)
        end_time = time.time() + max_expected_time

        incoming = ""
        while True:
            # Time left, read more data
            try:
                incoming += self.corenlp.read_nonblocking(2000, 1)
                if "\nNLP>" in incoming:
                    break
                time.sleep(0.0001)
            except pexpect.TIMEOUT:
                if end_time - time.time() < 0:
                    continue
                    logger.error("Error: Timeout with input '%s'" % (incoming))
                    return {'error': "timed out after %f seconds" % max_expected_time}
                else:
                    continue
            except pexpect.EOF:
                break

        
        if VERBOSE: 
            logger.info("%s\n%s" % ('='*40, incoming))
        try:
            results = parse_parser_results(incoming)
        except Exception as e:
            if VERBOSE: 
                logger.info(traceback.format_exc())
            raise e

        return results
    
    def parse(self, text):
        """ 
        This function takes a text string, sends it to the Stanford parser,
        reads in the result, parses the results and returns a list
        with one dictionary entry for each parsed sentence, in JSON format.
        """
        response = self._parse(text)
        if VERBOSE:
            logger.info("Response: '%s'" % (response))
        return response

    def parse_file(self, filename):
        with open (filename, "r") as f:
            data=unidecode.unidecode(f.read().decode("utf8").replace("\n"," "))
        return self.parse(data)


def ParseAndSaveFile(filename):
    if not os.path.isfile(filename + ".parsed"):
        shellout = "cat '%s' | %s  >> '%s.parsed'" % (filename, start_corenlp, filename)
        call(shellout, shell=True)
    with open (filename + ".parsed", "r") as f:
        data=f.read().decode("utf8")
    return parse_parser_results(unidecode.unidecode(data))

if __name__ == '__main__':
    """
    The code below starts an JSONRPC server
    """
    parser = optparse.OptionParser(usage="%prog [OPTIONS]")
    parser.add_option('-p', '--port', default='10003',
                      help='Port to serve on (default: 10002)')
    parser.add_option('-H', '--host', default='127.0.0.1',
                      help='Host to serve on (default: 127.0.0.1. Use 0.0.0.0 to make public)')
    options, args = parser.parse_args()
    server = jsonrpc.Server(jsonrpc.JsonRpc20(),
                            jsonrpc.TransportTcpIp(addr=(options.host, int(options.port))))
    
    nlp = StanfordCoreNLP()
    server.register_function(nlp.parse)
    server.register_function(nlp.parse_file)
    
    logger.info('Serving on http://%s:%s' % (options.host, options.port))
    server.serve()
