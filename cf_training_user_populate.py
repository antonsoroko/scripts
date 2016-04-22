#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import sys
import requests
import json
import time
import datetime
import string
from random import sample
from os import linesep
from urlparse import urljoin


VM_TYPES = {"Default Ubuntu Server": {"Description": "An AWS virtual machine with Ubuntu", "Index": 0},
            "MicroPCF": {"Description": "Pivotal Cloud Foundry installed on a single machine", "Index": 1},
            "Single-VM CF": {"Description": "Cloud Foundry installed on a single AWS virtual machine", "Index": 2}
}

AWS_REGIONS = ['us-east-1', 'us-west-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'sa-east-1']

def gen_password(length=8):
    chars = string.letters + string.digits
    return ''.join(sample(chars,length))

def main():
    parser = argparse.ArgumentParser(description='Create users in CF Training platform and jumpboxes for them')
    parser.add_argument("url", metavar='URL', type=str, help="URL of CF Training platform")
    parser.add_argument("awsaccesskey", metavar='AwsAccessKey', type=str, help="AWS Secret Key")
    parser.add_argument("awssecretkey", metavar='AwsSecretKey', type=str, help="AWS Secret Key")
    parser.add_argument("-c", "--count", metavar='COUNT', type=int, help="number of users to create", default=2)
    parser.add_argument("-f", "--file", metavar='FILE', type=str, help="Output file")
    parser.add_argument("--username-prefix", metavar='USERPREFIX', type=str, help="Prefix for naming users", default="user")
    parser.add_argument("--dont-create-vm", action='store_true', help="don't create VM for user")
    parser.add_argument("--vm-type", metavar='VMTYPE', type=str, help="VM type", choices=VM_TYPES.keys(), default=VM_TYPES.keys()[1])

    args = parser.parse_args()
    #print args

    data = []
    cur_date = datetime.datetime.now().strftime("%Y%m%d")
    mail_domain = "test.local"
    BASE_URL = args.url
    for i in range(args.count):
        client = requests.session()
        URL = urljoin(BASE_URL, '/get-user')
        #print "get xsrf"
        r = client.get(URL)
        cookies={}
        new_cookie = requests.utils.dict_from_cookiejar(r.cookies)
        cookies.update(new_cookie)
        xsrf_name = "X-XSRF-TOKEN"
        xsrf_value = cookies["XSRF-TOKEN"]
        URL = urljoin(BASE_URL, '/register')
        username = "{0}_{1}_{2}".format(args.username_prefix, cur_date, i)
        password = gen_password()
        register_data = dict(Email='{}@{}'.format(username, mail_domain),
                             Username=username,
                             Password=password,
                             Confirm=password)
        headers = {xsrf_name: xsrf_value, 'Content-Type': 'application/json'}
        #print "create user %s" % username
        #print register_data
        r = client.post(URL, data=json.dumps(register_data), headers=headers, cookies=cookies)
        if r.ok:
            #print register_data["Email"] + "," + register_data["Password"]
            data.append(register_data)
        else:
            print "error when creating user {}: {}".format(register_data, r.text)
        new_cookie = requests.utils.dict_from_cookiejar(r.cookies)
        cookies.update(new_cookie)

        if not args.dont_create_vm:
            URL = urljoin(BASE_URL, '/infrastructure/create')
            vm_type = args.vm_type
            aws_region = AWS_REGIONS[i % len(AWS_REGIONS)]
            infrastructure_data = dict(Name="auto_created_training_VM_for_{}".format(username),
                                       Credentials=dict(AwsAccessKey=args.awsaccesskey,
                                                        AwsSecretKey=args.awssecretkey,
                                                        AwsRegion=aws_region),
                                       OptionName=vm_type,
                                       OptionDescription=VM_TYPES[vm_type]["Description"],
                                       Configurator="aws_ami",
                                       ConfiguratorIndex=VM_TYPES[vm_type]["Index"],
                                       SupportsRestart="true")
            #print "creating VM for %s" % username
            #print infrastructure_data
            r = client.post(URL, data=json.dumps(infrastructure_data), headers=headers, cookies=cookies)
            if r.ok:
                #print "Created VM: " + r.text
                pass
            else:
                print "error when creating VM for user {}: {}".format(username, r.text)
        time.sleep(1)

    output_file = open(args.file, 'w') if args.file else sys.stdout

    #print data

    for user in data:
        output_file.write("{0},{1}{2}".format(user['Email'], user['Password'], linesep))

    if output_file is not sys.stdout:
        output_file.close()

    sys.exit(0)


if __name__ == "__main__":
    main()

