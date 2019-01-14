#!/bin/bash

SERVER=172.17.21.68
SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
read -p 'username: ' USERNAME
read -sp 'password: ' PASSWORD
echo
RESPONSE="$(eval "curl -X POST --cacert ${SCRIPTPATH}/codesigning_cert.pem -d \"username=${USERNAME}&password=${PASSWORD}\" \
	https://${SERVER}:5000/login 2>/dev/null")"
ERROR="$(echo "$RESPONSE" | python -c 'import sys, json; print json.load(sys.stdin)["error"]')"
MSG="$(echo "$RESPONSE" | python -c 'import sys, json; print json.load(sys.stdin)["msg"]')"
if [ "$ERROR" -ne 0 ]; then
	echo $MSG
	exit 1
fi
TOKEN="$(echo "$RESPONSE" | python -c 'import sys, json; print json.load(sys.stdin)["token"]')"
echo "Token: $TOKEN"
