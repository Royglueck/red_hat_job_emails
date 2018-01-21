#!/bin/bash
set -e

# Get Virtualenv Directory Path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT_NAME="scraper"
VIRTUAL_ENV_DIR="$SCRIPT_DIR/rh"

virtualenv -p python3.5 $VIRTUAL_ENV_DIR
source $VIRTUAL_ENV_DIR/bin/activate
pip3 install -r requirements.txt

echo "Using virtualenv located in $VIRTUAL_ENV_DIR ..."

# If the zip archive already exists, back it up
if [ -f $SCRIPT_DIR/$SCRIPT_NAME.zip ]; then
    mv $SCRIPT_DIR/$SCRIPT_NAME.zip $SCRIPT_DIR/$SCRIPT_NAME.zip.backup
    echo "Archive already exists; creating backup."
fi

# Add virtualenv libs to the new zip file
cd $VIRTUAL_ENV_DIR/lib/python3.5/site-packages
zip -qr9 $SCRIPT_DIR/$SCRIPT_NAME.zip *
cd $SCRIPT_DIR

# Add python code to the zip file
zip -qr9 $SCRIPT_DIR/$SCRIPT_NAME.zip $SCRIPT_NAME.py

# Deploy the code to AWS!
#terraform apply
