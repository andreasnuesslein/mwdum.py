#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys,re, copy
from random import random
from dateutil.parser import parse
from datetime import datetime


try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

uprint = lambda text: sys.stdout.buffer.write((text+'\n').encode('utf-8'))
#uprint = lambda x: "" if x else ""


def escapeSQL(string):
    newstr = ""
    newstr = string.replace('\\','\\\\')\
            .replace('"','\\"')\
            .replace('\'','\\\'')\
            .replace('\u0000','\\0')\
            .replace('\n','\\n')\
            .replace('\r','\\r')\
            .replace('\u001a','\\Z')\

    return "'%s'" % newstr

""" Models for the XML-Structure """
class Contributor:
    pass

class Rev:
    pass

class Page:
    def __init__(self):
        self.revs = []
    def __repr__(self):
        ret = ["%s: %s" %(k,v) for k,v in
                sorted(self.__dict__.items(),
                    key=lambda x: x[0])
                if not k=='revs' ]
        return(", ".join(ret))


class PageGenerator:
    def __init__(self, output_function):
        self.stack = []
        self.output_function = output_function
    def __repr__(self):
        return("Page: %s\nRev: %s" %(self.page,self.revision))

    def newE(self, elem):
        if elem == 'page':
            e = Page()
        elif elem == 'revision':
            e = Rev()
        elif elem == 'contributor':
            e = Contributor()
        setattr(self,elem,e)
        self.stack.append(elem)

    def addAttr(self, attr, value):
        try:
            elem = getattr(self, self.stack[-1])
            setattr(elem, attr, value)
        except:
            pass

    def pop(self):
        elem = self.stack.pop()
        if elem == 'contributor':
            self.revision.contributor = self.contributor
            del(self.contributor)
        elif elem == 'revision':
            self.page.revs.append(self.revision)
            del(self.revision)
        elif elem == 'page':
            self.output_function(self.page)
            del(self.page)



class MWDump:
    def __init__(self, input_file):
        self.ETip = ET.iterparse(input_file,events=("start","end"))
        first = next(self.ETip)[1]
        self.ns = first.tag[:-len('mediawiki')]
        self.els = []

    def output_mysql(self, page):

        ## revs ##
        text = []

        revarray = []

        latest_rev = sorted(page.revs, key=lambda x: x.timestamp)[-1]

        for rev in page.revs:
            if not rev.text:
                rev.text = ''
            text += [(rev.id, escapeSQL(rev.text))]

            try:
                comment = escapeSQL(rev.comment)
            except:
                comment = "''"

            minor = 1 if 'minor' in rev.__dict__.keys() else 0
            deleted = 1 if 'deleted' in rev.__dict__.keys() else 0
            try:
                user = rev.contributor.id
                user_text = escapeSQL(rev.contributor.username)
            except:
                user = 0
                try:
                    user_text = "'%s'" % (rev.contributor.ip)
                except:
                    user_text = "''"

            if 'deleted' in rev.__dict__.keys():
                import ipdb;ipdb.set_trace()
                """ LOOK THERES A DELETED FLAG"""

            timestamp = parse(rev.timestamp).strftime('%Y%m%d%H%M%S')  # obviously works better but is slower

            revarray += ["(%s, %s, %s, %s, %s, %s, '%s', %s, %s)" %(
                    rev.id, page.id, rev.id, comment, user, user_text,
                    timestamp, minor, deleted ) ]


        ## page ##
        touched = datetime.now().strftime('%Y%m%d%H%M%S')
        try:
            title = escapeSQL(page.title.replace(" ","_"))
        except:
            title = ""
        redirect = 1 if 'redirect' in page.__dict__.keys() else 0
        ins = "page_id,page_namespace,page_title,page_is_redirect,page_random,page_touched,page_latest,page_len"
        val = "%s,%s,%s,%s,%s,%s,%s,%s" %(
                page.id, page.ns, title, redirect,
                random(), touched, latest_rev.id, len(latest_rev.text))

        try:
            v = page.restrictions
            ins += ',page_restrictions'
            val += ",'%s'" %v
            import ipdb;ipdb.set_trace()
            """ LETS CHECK OUT RESTRICTIONS """
        except:
            pass

        sql = "INSERT INTO page(%s) VALUES (%s);" %(ins,val)
        uprint(sql)

        ### text ###
        val = ",".join(["(%s,%s,'utf-8')" %(tid,txt) for tid,txt in text])
        sql = "INSERT INTO text(old_id,old_text,old_flags) VALUES %s;" %(val)
        uprint(sql)

        #### revisions ###
        ins = "INSERT INTO revision (rev_id,rev_page,rev_text_id,rev_comment,rev_user,rev_user_text,rev_timestamp,rev_minor_edit,rev_deleted) VALUES %s;"
        val = ",".join(revarray)
        sql = ins % (val)
        uprint(sql)




    def run(self):
        pg = PageGenerator(self.output_mysql)
        for ev, el in self.ETip:
            cleanTag = el.tag[len(self.ns):]

            if cleanTag in ['page','revision','contributor']:
                if ev == 'start':
                    pg.newE(cleanTag)
                if ev == 'end':
                    pg.pop()
                el.clear()
            else:
                pg.addAttr(cleanTag,el.text)

            self.els.append(el)




mwd = MWDump(sys.argv[1])
mwd.run()
