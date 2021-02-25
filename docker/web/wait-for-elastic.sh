#!/bin/sh
# wait-for-elastic.sh

set -e

host="$1"
shift

until curl --silent --output /dev/null http://$host:9200/_cat/health?h=st; do printf '.'; sleep 1; done; printf '\nelastic is up\n'
