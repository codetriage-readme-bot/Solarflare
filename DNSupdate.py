import re
import requests
import os
import json
from sys import argv

if list({'-v','--verbose'} & {arg.lower() for arg in argv}):
    verbose=True


resourceTypes={'A','MX'}

def verifyCredentials(email,APIkey):
    r = requests.get('https://api.cloudflare.com/client/v4/user',headers={'X-Auth-Email':email,'X-Auth-Key':APIkey})
    return True if r.json()['success'] else False

#Prompt for and verify Cloudflare credentials
def getCredentials():
    e=input('Email: ')
    k=input('API key: ')
    if verifyCredentials(e,k):
        return {'email':e,'key':k}
    else:
        print('Invalid Credentials!')
        return getCredentials()

#Yes or No question
def choice(query):
    c = input(query).lower()
    if 'y' in c:
        return True
    elif 'n' in c:
        return False
    else:
        print('Invalid Entry!')
        return choice(query)
print(os.path.join(os.path.dirname(os.path.normpath(__file__)),'config.json'))
if os.path.exists(os.path.join(os.path.dirname(os.path.normpath(__file__)),'config.json')):
    with open('config.json','r') as configf:
        config=json.load(configf)
else:
    print("No config found.  Entering setup.")
    config=getCredentials()
    zones={z['id']:dict() for z in requests.get("https://api.cloudflare.com/client/v4/zones",headers={'X-Auth-Email':config['email'],'X-Auth-Key':config['key']}).json()['result']}
    print(zones)
    for z in zones.keys():
        print("Checking ZoneID "+z)
        for r in requests.get('https://api.cloudflare.com/client/v4/zones/{}/dns_records'.format(z),headers={'X-Auth-Email':config['email'],'X-Auth-Key':config['key']}).json()['result']:
            if verbose: print("Record type: "+r['type'])
            if choice('Activate DDNS for '+r['name'] +' [Y/N]') and r['type'] in resourceTypes:
                zones[z][r['id']] = {'name':r['name'],'type':r['type'],'proxied':False if not r['proxiable'] else r['proxied']}
    config['zones']=zones
    print("Writing config...")
    with open('config.json','w') as configf:
        configf.write(json.dumps(config))
    print('Done.  Deleting config.json in the future will reset configuration.')


def fetch(server):
    '''
    This function gets your external IP from a specific server
    '''
    content=requests.get(server).text
    m = re.search(
            '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)',
            content)
    myip = m.group(0)
    return myip if len(myip) > 0 else 'noip'

#Updates Cloudflare's DNS records for specified domains in a zone.
def recordUpdate(zoneID,record,IP):
    global config
    r= requests.put('https://api.cloudflare.com/client/v4/zones/{0}/dns_records/{1}'.format(zoneID,id),json={'type':record['type'],'name':record['name'],'content':IP,'proxied':record['proxied']},headers={'X-Auth-Email':config['email'],'X-Auth-Key':config['key']})
    if verbose: print("Set DNS for "+record['name'])

#Get external IP address.  Try two different sites in case one is non-functional.
try:
    IP=fetch('https://api.ipify.org')
    print("Using IPify")
except:
    IP = fetch('http://ipchicken.com')
    print("Using IPchicken")

print('Retrieved IP Address: '+ str(IP))
if verbose: print('------Configuration------ \n\n'+config+'\n\n')

#Update DNS records for selected domains within each zone.
for zone in config['zones']:
    for record in config['zones'][zone]:
        if verbose: print(config['zones'][zone][record])
        recordUpdate(zone,config['zones'][zone][record],IP)




