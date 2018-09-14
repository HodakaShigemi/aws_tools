#!/usr/bin/env python
# -*- coding: utf-8 -*-
from botocore.session import Session
import sys

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
if credentials.token is None:
    print("echo 'Profile \"{}\" seeems not to be a Role. exit' >&2;false".format(profile))
    exit(1)
print("export AWS_ACCESS_KEY_ID={}".format(credentials.access_key))
print("export AWS_SECRET_ACCESS={}".format(credentials.secret_key))
print("export AWS_SESSION_TOKEN={}".format(credentials.token))
print('export OLD_PS1="$PS1"')
print('export PS1="({})$PS1"'.format(profile))
