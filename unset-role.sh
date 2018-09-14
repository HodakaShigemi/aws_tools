#!/bin/bash
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY
unset AWS_SESSION_TOKEN
if [ -n "$OLD_PS1" ];then
    export PS1="$OLD_PS1"
    unset OLD_PS1
fi
