#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import json
import sqlite3
import collections

import jinja2

SQL_GET_PACKAGES = '''
SELECT
  name, category, section, pkg_section, version, release, description, dep.dependency
FROM packages
LEFT JOIN (
    SELECT
      package,
      group_concat(dependency || '|' || version || '|' || relationship) dependency
    FROM package_dependencies
    GROUP BY package
  ) dep
  ON dep.package = packages.name
ORDER BY category, section, name
'''

DEP_REL = collections.OrderedDict((
    ('PKGDEP', 'Depends'),
    ('BUILDDEP', 'Depends (build)'),
    ('PKGREP', 'Replaces'),
    ('PKGRECOM', 'Recommends'),
    ('PKGCONFL', 'Conflicts'),
    ('PKGBREAK', 'Breaks')
))

RE_QUOTES = re.compile(r'"([a-z]+|\$)"')

def gen_trie(wordlist):
    trie = {}
    for word in wordlist:
        p = trie
        for c in word:
            if c not in p:
                p[c] = {}
            p = p[c]
        p['$'] = 0
    return trie

def read_db(filename):
    db = sqlite3.connect(filename)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    packages = []
    for row in cur.execute(SQL_GET_PACKAGES):
        pkg = dict(row)
        dep_dict = {}
        if row[-1]:
            for dep in row[-1].split(','):
                dep_pkg, dep_ver, dep_rel = dep.split('|')
                if dep_rel in dep_dict:
                    dep_dict[dep_rel].append((dep_pkg, dep_ver))
                else:
                    dep_dict[dep_rel] = [(dep_pkg, dep_ver)]
        pkg['dependency'] = dep_dict
        packages.append(pkg)
    return packages

def render_html(**kwargs):
    jinjaenv = jinja2.Environment(loader=jinja2.FileSystemLoader(
        os.path.normpath(os.path.join(os.path.dirname(__file__), 'templates'))))
    jinjaenv.filters['strftime'] = (
        lambda t, f='%Y-%m-%dT%H:%M:%SZ': time.strftime(f, t))
    template = jinjaenv.get_template(kwargs.get('template', 'template.html'))
    kvars = kwargs.copy()
    kvars['updatetime'] = time.gmtime()
    trie = json.dumps(gen_trie(p['name'] for p in kwargs['packages']), separators=',:')
    kvars['packagetrie'] = RE_QUOTES.sub('\\1', trie).replace('{$:0}', '0')
    kvars['dep_rel'] = DEP_REL
    return template.render(**kvars)

def main(filename='abbs.db'):
    packages = read_db(filename)
    html = render_html(title='AOSC Package List', packages=packages)
    print(html)

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
