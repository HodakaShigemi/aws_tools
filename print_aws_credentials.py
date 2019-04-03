#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from botocore.session import Session
import sys
import os

try:
    profile = sys.argv[1]
except IndexError:
    print("echo 'Error: Please pass an argument PROFILE_NAME' >&2;false")
    exit(1)

available_profiles = Session().available_profiles
if not profile in available_profiles:
    print("echo \"Error: {} is not available. \\nAvailable profiles are {}\" >&2;false".format(profile, available_profiles))
    exit(1)

credentials = Session(profile=profile).get_credentials()
print("export AWS_ACCESS_KEY_ID={}".format(credentials.access_key))
print("export AWS_SECRET_ACCESS_KEY={}".format(credentials.secret_key))
if credentials.token:
    print("export AWS_SESSION_TOKEN={}".format(credentials.token))
if os.environ.get('OLD_PS1'):
    print('export PS1="({})$OLD_PS1"'.format(profile))
else:
    print('export OLD_PS1="$PS1"')
    print('export PS1="({})$PS1"'.format(profile))
