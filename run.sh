#!/bin/bash

if [ ! -n "$1" ]; then
    port=8888
else
    port=$1
fi

python socket_server.py --port=$port
