from distutils.core import setup

setup(name = "artrat",
      version = "1",
      description = "",
      author = "JoYo",
      author_email = "jvictor@stanford.edu",
      url = "",
      packages = ['artrat'],
      package_data={'artrat': ['stanford-corenlp-full-2015-01-29/*.jar',
                               'stanford-corenlp-full-2015-01-29/*.xml',
                               'stanford-corenlp-full-2015-01-29/*.txt',
                               'stanford-corenlp-full-2015-01-29/patterns/*',
                               'stanford-corenlp-full-2015-01-29/tokensregex/*',
                               'stanford-corenlp-full-2015-01-29/sutime/*',
                               'default.properties',
                               '*.txt']},
      include_package_data=True
      ) 
