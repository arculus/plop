#!/usr/bin/env python
from collections import Counter
import logging
import os

from tornado.ioloop import IOLoop
from tornado.options import define, options, parse_command_line
from tornado.web import RequestHandler, Application
import six

from plop.callgraph import CallGraph, profile_to_json

define('port', default=8888)
define('debug', default=False)
define('address', default='')
define('datadir', default='profiles')

class IndexHandler(RequestHandler):
    def get(self):
        files = []
        for filename in os.listdir(options.datadir):
            mtime = os.stat(os.path.join(options.datadir, filename)).st_mtime
            files.append((mtime, filename))
        # sort by descending mtime then ascending filename
        files.sort(key=lambda x: (-x[0], x[1]))
        self.render('index.html', files=[f[1] for f in files])

class ViewHandler(RequestHandler):
    def get(self):
        self.render('force.html', filename=self.get_argument("filename"))

class ViewFlatHandler(RequestHandler):
    def get(self):
        self.render('force-flat.html',
                    data=profile_to_json(self.get_argument('filename')))

    def embed_file(self, filename):
        with open(os.path.join(self.settings['static_path'], filename)) as f:
            return f.read()

class DataHandler(RequestHandler):
    def get(self):
        self.write(profile_to_json(self.get_argument('filename')))

def main():
    parse_command_line()

    handlers = [
        ('/', IndexHandler),
        ('/view', ViewHandler),
        ('/view-flat', ViewFlatHandler),
        ('/data', DataHandler),
        ]

    settings=dict(
        debug=options.debug,
        static_path=os.path.join(os.path.dirname(__file__), 'static'),
        template_path=os.path.join(os.path.dirname(__file__), 'templates'),
        )

    app = Application(handlers, **settings)
    app.listen(options.port, address=options.address)
    print("server starting at http://%s:%s" % (options.address or 'localhost',
                                               options.port))
    IOLoop.instance().start()

if __name__ == '__main__':
    main()
