sudo cp ./prefect-flow-slack-backup.service /etc/systemd/system/
sudo systemctl enable prefect-flow-slack-backup.service
sudo service prefect-flow-slack-backup start
sudo service prefect-flow-slack-backup status