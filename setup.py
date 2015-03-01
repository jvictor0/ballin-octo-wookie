from distutils.core import setup

setup(name = "artrat",
      version = "1",
      description = "",
      author = "JoYo",
      author_email = "jvictor@stanford.edu",
      url = "",
      packages = ['artrat'],
      package_data={'artrat': ['stanford-corenlp-full-2014-08-27/*.jar',
                               'stanford-corenlp-full-2014-08-27/*.xml',
                               'stanford-corenlp-full-2014-08-27/*.txt',
                               'stanford-corenlp-full-2014-08-27/patterns/*',
                               'stanford-corenlp-full-2014-08-27/tokensregex/*',
                               'stanford-corenlp-full-2014-08-27/sutime/*',
                               'default.properties',
                               '*.txt']},
      include_package_data=True
      ) 
