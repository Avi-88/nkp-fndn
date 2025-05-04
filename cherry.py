#!/usr/bin/env python2
# webserver.py
import subprocess
import cherrypy

class Root(object):
    def index(self):
        def content():
            proc = subprocess.Popen(['python', 'slowprint.py'], stdout=subprocess.PIPE)
            line = proc.stdout.readline()
            while line:
                yield line
                line = proc.stdout.readline()
        return content()
    index.exposed = True
    index._cp_config = {'response.stream': True}

cherrypy.quickstart(Root())