if [ -f $0 ];then
    echo "Usage: \"source $0 PROFILE_NAME\"  or \" . $0 PROFILE_NAME\"" >&2
    exit 1
else
    eval $(~/.aws/print_aws_credentials.py $1)
fi
