#!/bin/bash
NAME="blockade"                                  # Name of the application
WORKDIR=/opt/cloud_node/
echo "Starting $NAME as `whoami`"

# Activate the virtual environment
cd $WORKDIR
source venv/bin/activate
cd $WORKDIR/app

# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec uwsgi --ini wsgi.ini
