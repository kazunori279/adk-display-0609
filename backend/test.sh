#!/bin/bash

# Set SSL certificate file for secure connections
export SSL_CERT_FILE=$(python -m certifi)

# Run pytest with SSL certificate configured
echo "Running tests with SSL_CERT_FILE: $SSL_CERT_FILE"
python -m pytest "$@"