#!/usr/bin/env python

## Defaults section
## Modify values here to affect defaults
## Arguments listed are all andatory
## Remove or add arguments to this list 
## Script will return exit code 5 if an 
## argument has an empty value, so either define one
## below, or set it to None so that a user must pass 
## a value for that argument

args = {
        'ip'                : None,
        'dns'                : None,
        'netmask'        : None,
        'gateway'        : None,
        'rhevcluster'        : 'Default',
        'rhevmhost'        : 'host.domain.com',
        'rhevmport'        : '8443',
        'rhevmuser'        : None,
        'rhevmpass'        : None,
        'buildvm'        : None,
        'memory'        : '1',
        'disksize'        : '40',
        'cores'                : '1',
        'kickstart'        : None,
        'vlan'                : None,
        'bootinitrd'        : '/mnt/isolinux/initrd.img',
        'bootvmlinuz'        : '/mnt/isolinux/vmlinuz',
        'diskinterface'        : 'virtio',
        'diskformat'        : 'cow',
        'disksparse'        : 'true',
        'diskbootable'        : 'true',
        'diskwipe'        : 'true',
        'disktype'        : 'system',
        'nicname'        : 'nic1',
        'storagedomain'        : 'storage0',
        'storagetype'        : 'system',
        'vmtemplate'        : 'Blank',
        'vmtype'        : 'server',
        'displaytype'        : 'vnc',
} 

def usage(args): 
        print "Usage: %s " % sys.argv[0]
        for arg in sorted(args.keys()):
                if args[arg] == None: 
                        print "\t --%s=<value>" % (arg)
                else:
                        print "\t [ --%s=<value> ] (default: %s)" % (arg, args[arg])
        

## base64 to hash password
## urllib2 to make HTTP(s) requests for REST
## sys to parse commandline arguments
## re (regex) to match HTTP responses
## getopt for cli argument parsing
## time for sleep()
import base64, urllib2, sys, re, getopt, time

## XML parsing library, change namespace 
import elementtree.ElementTree as xml

## Use the Python Debugger to troubleshoot
## Starts the program in interactive mode
## You will be prompted after each line runs
## Enter "next" to proceed to the next line
import pdb
#pdb.set_trace()

## Returns encoded string we can stuff in HTTP header 
## to provide HTTP Basic authentication 

def auth_request_header(username, password):
        authstring = base64.encodestring('%s:%s' % (username, password)).strip()
        return authstring


## Make an HTTP GET request to a URL

def rest_get(url, authstring):
        request = urllib2.Request(url)
        request.add_header("Authorization", "Basic %s" % authstring)
        getdata = None
        try:
                getdata = urllib2.urlopen(request)
        except urllib2.URLError, e:
                ## supplied version of urllib2 throws a URLError exception on 201 and 202
                if re.match('20.:', str(e)):
                        out = re.sub('*:', '', e)
                        print "Success : %s" % (out)
                        pass
                else:
                        print "Error: cannot get URL : %s" % (e)
                        sys.exit(10)
        return getdata


## Make an HTTP POST request to a URL
## All POSTS to RHEV API should be in XML format

def rest_post(url, authstring, postdata): 
        request = urllib2.Request(url)
        request.add_header("Authorization", "Basic %s" % authstring)
        getdata = None
        request.add_header('Content-Type', 'application/xml')
        try: 
                request.get_method = lambda: 'POST'
                getdata = urllib2.urlopen(request, postdata)
        except urllib2.URLError, e:
                ## supplied version of urllib2 throws a URLError exception on 201 and 202
                if re.match('20.:', str(e)):
                        out = re.sub('*:', '', e)
                        print "Success : %s" % (out)
                        pass
                else:
                        print "Error: cannot get URL : %s" % (e)
        return getdata
        

## Returns XML document necessary to create a VM
## Name, cluster, template and memory are mandatory
## Set display type to VNC; default is SPICE
## VM types are enumerated in the RHEV-M capabilities section
## VM types can be user-defined; default install supplies
## "desktop" and "server" and defaults to "desktop"
## See RHEV REST API spec for all possible keys/values
## http://red.ht/wNPFTu

def xml_create_vm(vmname, cluster, memory, vmtype, template, displaytype): 
        size_in_bytes = str(int(memory)*2**10*2**10*2**10)
        vm = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <vm>
                <name>""" + vmname + """</name>
                <type>""" + vmtype + """</type>
                <cluster>
                        <name>""" + cluster + """</name>
                </cluster>
                <template>
                        <name>""" + template + """</name>
                </template>
                <memory>""" + size_in_bytes + """</memory>
                <display>
                        <type>""" + displaytype + """</type>
                </display>
        </vm> """
        return vm


## Return XML document necessary to allocate storage to a VM
## Values included here are all mandatory

def xml_create_storage(stgid, size, type, interface, format, sparse, bootable, wipe ):
        size_in_bytes = str(int(size)*2**10*2**10*2**10)
        storage = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <disk>
                <storage_domains>
                        <storage_domain id=\"""" + stgid + """\" />
                </storage_domains>
                <size>""" + size_in_bytes + """</size>
                <type>""" + type + """</type>
                <interface>""" + interface + """</interface>
                <format>""" + format + """</format>
                <sparse>""" + sparse + """</sparse>
                <bootable>""" + bootable + """</bootable>
                <wipe_after_delete>""" + wipe + """</wipe_after_delete>
        </disk> """
        return storage


## Return XML document necessary to allocate NIC to a VM
## Interface type, name and network (VLAN) are mandatory

def xml_create_network(nicname, vmname, network): 
        network = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <nic>
                <interface>virtio</interface>
                <name>""" + nicname + """</name>
                <network>
                        <name>""" + network + """</name>
                </network>
        </nic> """
        return network


## Return XML document necessary to start a VM in run-once mode for install

def xml_run_once(kickstart, ip, netmask, gateway, dns): 
        initrd = '/mnt/isolinux/initrd.img'
        vmlinuz = '/mnt/isolinux/vmlinuz'
        bootargs = "ks=" + kickstart + " ksdevice=link ip=" + ip + " netmask=" + netmask + " gateway=" + gateway + " dns=" + dns
        action =  """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <action>
                <vm>
                        <stateless>true</stateless>
                        <os>
                                <kernel>""" + vmlinuz + """</kernel>
                                <initrd>""" + initrd + """</initrd>
                                <cmdline>""" + bootargs + """</cmdline>
                        </os>
                </vm>
        </action> """
        return action

## Takes a VM name and returns a VM ID necessary for modifying a VM
## ex: find_vm_id(RHEVM_USER, RHEVM_PASS, "vx17ba")

def find_vm_id(authstring, baseurl, vmname): 
        url = baseurl + "vms?search=" + vmname
        doc = rest_get(url, authstring) 
        tree = xml.parse(doc)
        matches = tree.findall("vm")
        if len(matches) == 0 : 
                print "Failed to find VM %s" % (vmname)
                return None
        else: 
                return matches[0].attrib["id"]
        

## Finds the first cluster, either with a specified name, or first available
## ex: find_cluster_name(RHEVM_USER, RHEVM_PASS, None)
## ex: find_cluster_name(RHEVM_USER, RHEVM_PASS, "Default")

def first_cluster_named(authstring, baseurl, cluname): 

        if cluname == None : 
                url = baseurl + "clusters"
        else:
                url = baseurl + "clusters?search=" + cluname

        doc = rest_get(url, authstring) 
        tree = xml.parse(doc)
        matches = tree.findall("cluster")
        if len(matches) == 0 : 
                print "Failed to find cluster %s" % (cluname)
                return None
        else: 
                return matches[0].find("name").text

## Finds the first vlan, either with a specified name, or first available
## ex: find_cluster_name(RHEVM_USER, RHEVM_PASS, None)
## ex: find_cluster_name(RHEVM_USER, RHEVM_PASS, "Default")

def first_vlan_named(authstring, baseurl, vlan): 

        url = baseurl + "networks"

        doc = rest_get(url, authstring) 
        tree = xml.parse(doc)
        matches = tree.findall("network")
        for match in matches: 
                if match.find("name").text == vlan:
                        return matches[0].find("name").text

        print "Failed to find vlan %s" % (vlan)
        return None

def wait_for_vm(authstring, baseurl, vmid): 
        url = baseurl + "vms/" + vmid
        status = None
        while status != "down": 
                doc = rest_get(url, authstring)
                tree = xml.parse(doc)
                matches = tree.findall("status")
                status = matches[0].find("state").text
                time.sleep(1)
        
        
## Takes a disk size and optional storage domain name and returns the storage
## domain ID only if the space requested is available
## ex: find_storage_id(authstring, None, DISK)
## ex: find_storage_id(authstring, "storage2", DISK)

def find_storage_id(authstring, baseurl, name, size): 

        if name == None : 
                url = baseurl + "storagedomains"
        else:
                url = baseurl + "storagedomains?search=" + name

        doc = rest_get(url, authstring) 
        tree = xml.parse(doc)
        matches = tree.findall("storage_domain")
        if len(matches) == 0 : 
                print "Failed to find storage domain %s" % (name)
                return None
        else: 
                index = 0
                size_in_bytes = int(size)*2**10*2**10*2**10
                while (index < len(matches)): 
                        if int(matches[index].find("available").text) >= size_in_bytes: 
                                return matches[0].attrib["id"]
                        else: index += 1
                print "Failed to find storage domain with %s gigabytes available " % (str(size))
                return None


## Finds the first vlan, either with a specified name, or first available
## ex: find_network_name(RHEVM_HOST, RHEVM_PORT, RHEVM_USER, RHEVM_PASS, None)

def find_network_name(authstring, baseurl, vlan): 

        url = baseurl + "networks"
        doc = rest_get(url, authstring) 
        tree = xml.parse(doc)
        matches = tree.findall("network")
        return matches[0].find("name").text


def main(argv, args):
        #pdb.set_trace()
        
        arglist = list()
        for arg in args.keys():
                arglist.append(arg + "=")        

        try:
                cliopts, cliargs = getopt.getopt(argv, "", arglist)

        except getopt.GetoptError, e:
                print e
                usage(args)
                sys.exit(5)

        for cliopt, cliarg in cliopts:
                opt = re.sub("--", "", cliopt)
                args[opt] = cliarg

        for arg in args.keys(): 
                if [arg] == None:
                        print "--- Required argument %s not defined! ---" % (arg)
                        usage(args)
                        sys.exit(5)

        authstring = auth_request_header(args['rhevmuser'], args['rhevmpass'])
        baseurl = "https://" + args['rhevmhost'] + ":" + args['rhevmport'] + "/api/"

        ## Resolve usable cluster, vlan, storage
        cluster = first_cluster_named(authstring, baseurl, args['rhevcluster'])
        if cluster == None:
                sys.exit(6)
        vlan = first_vlan_named(authstring, baseurl, args['vlan'])
        if vlan == None:
                sys.exit(7)
        storageid = find_storage_id(authstring, baseurl, args['storagedomain'], args['disksize'])
        if storageid == None:
                sys.exit(8)

        ## Define the VM
        url = baseurl + "vms"
        vmxml = xml_create_vm(args['buildvm'], cluster, args['memory'], args['vmtype'], args['vmtemplate'], args['displaytype'])
        print "Creating VM shell %s on cluster %s size %s" % (args['buildvm'], args['rhevcluster'], args['memory'])
        rest_post(url, authstring, vmxml) 

        ## Find the ID of the guest we just created
        vmid = find_vm_id(authstring, baseurl, args['buildvm'])

        ## Add network to the vm
        url = baseurl + "vms/" + vmid + "/nics" 
        netxml = xml_create_network(args['nicname'], args['buildvm'], vlan)
        print "Creating network %s on vm %s on vlan %s" % (args['nicname'], args['buildvm'], vlan)
        rest_post(url, authstring, netxml) 

        ## Add storage to the vm
        url = baseurl + "vms/" + vmid + "/disks" 
        storagexml = xml_create_storage(storageid, args['disksize'], args['disktype'], 
                args['diskinterface'], args['diskformat'], args['disksparse'], 
                args['diskbootable'], args['diskwipe'] )
        print "Creating storage on vm %s on domain %s size %s" \
                % (args['buildvm'], args['storagedomain'], args['disksize']) 
        rest_post(url, authstring, storagexml) 
        

        ## Kick off a build
        ## wait for the previous vm settings to take effect, or we'll get an error 400
        ## FIXME - find a way to check for completion, rather than dumbly sleeping
        #time.sleep(15)
        wait_for_vm(authstring, baseurl, vmid)
        print "Power on vm %s and run kickstart" % (args['buildvm'])
        url = baseurl + "vms/" + vmid + "/start" 
        runxml = xml_run_once(args['kickstart'], args['ip'], args['netmask'], args['gateway'], args['dns'])
        rest_post(url, authstring, runxml) 

if __name__ == "__main__":
        main(sys.argv[1:], args)
