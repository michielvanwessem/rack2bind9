#!/usr/bin/env python2.7

# Copyright (c) 2017, Michiel van Wessem <michiel.van.wessem@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# -*- coding: utf-8 -*-


from __future__ import print_function
from __future__ import unicode_literals

import time
import os

import boto3
import pyrax

DOMAIN_NAME = "example.com"
S3BUCKET = 'example-dns'
recordtypelist = []

thedate = time.strftime("%Y%m%d")
bindfile = "/tmp/example.com-dns-" + DOMAIN_NAME + "-" + thedate + ".txt"

# Use Rackspace provided credentials
pyrax.set_setting("identity_type", "rackspace")
creds_file = os.path.expanduser("~/.rack/rackspace_credentials")
pyrax.set_credential_file(creds_file)

dns = pyrax.cloud_dns
dns.set_timeout(10)
dom = dns.find(name=DOMAIN_NAME)

exportdns = dom.export()

# Start writing DNS Headers
bindheader = '; BIND db file for {0}\n'.format(DOMAIN_NAME)
bindorigin = '$ORIGIN {0}\n'.format(DOMAIN_NAME)
bindttl = '$TTL 300\n'

with open(bindfile, 'w') as target:
    target.truncate()
    target.write(bindheader)
    target.write(bindorigin)
    target.write(bindttl)

# Rewrite the list that we got from rackspace to a proper Bind9 format file.
for line in exportdns.splitlines():
    if 'SOA' in line:
        with open(bindfile, "a") as text_file:
            soarecord = line.split()
            print("{:<5}{:<5}{:<12}{:<20}{} (".format("@", soarecord[2], soarecord[3], soarecord[4], soarecord[5]), file=text_file)
            print("{0:>32} ; serial".format(soarecord[6]), file=text_file)
            print("{0:>32} ; time-to-refresh".format(soarecord[7]), file=text_file)
            print("{0:>32} ; time-to-retry".format(soarecord[8]), file=text_file)
            print("{0:>32} ; time-to-expire".format(soarecord[9]), file=text_file)
            print("{0:>32} ) ; minimum TTL".format(soarecord[10]), file=text_file)
    elif 'NS' in line:
        with open(bindfile, "a") as text_file:
            nsrecord = line.split()
            if 'aws' in nsrecord[0]:
                print("{:<30}{:<5}{:<6}{}".format(nsrecord[0], nsrecord[2], nsrecord[3], nsrecord[4]), file=text_file)
            else:
                print("{}{:>31}{:>5}{:>27}".format(" ", nsrecord[2], nsrecord[3], nsrecord[4]), file=text_file)
    else:
        # Any other record should be added to the general list
        recordtypelist.append(line)

with open(bindfile, "a") as text_file:
    print("\n".join(map(str, recordtypelist)), file=text_file)

# Upload this to S3. To our DNS bucket
print("Starting S3 Upload")
s3client = boto3.resource('s3')
with open(bindfile, 'rb') as data:
    s3object = bindfile.split("/")
    s3client.meta.client.upload_file(bindfile, S3BUCKET, s3object[2])

# Do some error checking on the above before removing below
# Clean up after we are done
if os.path.exists(filename):
    try:
        os.remove(filename)
        except OSError as e:
            print ("Error: %s - %s." % (e.filename,e.strerror))
    else:
        print("Sorry, I can not find %s file." % filename)
