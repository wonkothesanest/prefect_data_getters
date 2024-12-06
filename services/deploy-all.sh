#!/bin/bash

# Define the services directory
SERVICES_DIR="./services"

# Iterate over all .service files in the directory
for service_file in "$SERVICES_DIR"/*.service; do
    service_name=$(basename "$service_file")

    echo "Deploying $service_name..."

    # Copy the service file to the systemd directory
    sudo cp "$service_file" /etc/systemd/system/

    # Enable the service to start on boot
    sudo systemctl enable "$service_name"

    # Start the service
    sudo systemctl restart "$service_name"

    # Check the service status
    sudo systemctl status "$service_name" --no-pager
done

echo ""
echo "Deployment of all services completed."
