#!/usr/bin/env python

## static definitions

RHEVM_HOST = 'host.domain.com'
RHEVM_PORT = '8443'
RHEVM_USER = 'admin@internal'
RHEVM_PASS = 'pass'

PUTHOSTINMAINTMODE = 'host'

BASEURL = "https://" + RHEVM_HOST + ":" + RHEVM_PORT + "/api/"


import base64, urllib2
import elementtree.ElementTree as xml
## Use the Python Debugger to troubleshoot
import pdb

def build_authed_request(url, username, password):
        request = urllib2.Request(url)
        authstring = base64.encodestring('%s:%s' % (username, password)).strip()
        request.add_header("Authorization", "Basic %s" % authstring)
        return request

def rest_get(request):
        getdata = None
        try:
                getdata = urllib2.urlopen(request)
        except urllib2.URLError, e:
                print "Error: cannot get URL : %s" % (e)

        return getdata

def rest_parse(xmldata):
        ## just dump to screen for now
        parsed_data = xml.parse(xmldata)
        xml.dump(parsed_data)


def xml_bare_action(): 
        action = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <action/>"""
        return action

def find_host_id(rhevmuser, rhevmpass, name): 
        ## ex: find_host_id(RHEVM_USER, RHEVM_PASS, None)
        ## ex: find_host_id(RHEVM_USER, RHEVM_PASS, "omhq1bdf")

        if name == None : 
                url = BASEURL + "hosts"
        else:
                url = BASEURL + "hosts?search=" + name

        doc = rest_get(build_authed_request(url, rhevmuser, rhevmpass)) 
        tree = xml.parse(doc)
        # xml.dump(tree)
        matches = tree.findall("host")
        if len(matches) == 0 : 
                print "Failed to find cluster %s" % (name)
                return None
        else: 
                return matches[0].find("name").text
        
actionxml = xml_bare_action()
print "Put host %s in maintenance mode" % (PUTHOSTINMAINTMODE)
hostid = find_host_id(RHEVM_USER, RHEVM_PASS, PUTHOSTINMAINTMODE)
url = BASEURL + "hosts/" + hostid + "/maintenance"
response = rest_get(build_authed_request(url, RHEVM_USER, RHEVM_PASS),actionxml) 
rest_parse(response)

