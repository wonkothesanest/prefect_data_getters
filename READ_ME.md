So the configuration and setup of all this machine learning stuff is getting a little dense.

With all my goals we are starting to run into the need of having schedulers and processes to run either locally or in the cloud.  I'd prefer locally but I can't count on the machines always being running (unless I were running on a pi...)

Prefect.io seems like a good workflow manager 

ControlFlow.io seems like a good agentic flow manager that can also use langchain bots.
-- Too young.  Have also tried langgraph which was too cumbersome
now on to AutoGen, still on a naicent build but it is looking promising and easy to use (started another project)

Goals
start prefect on startup?
have a worker be running to preform tasks.
start a task with how long ago the last task was run
cron setup a process flow for getting slack data
on slack data store into a vector database
same store into an elasticsearch db.

Note: scripts assume venv dir
deploy scripts in config dir to /etc/systemd/system/
run
sudo systemctl enable prefect-server
sudo systemctl enable prefect-worker
sudo systemctl start prefect-server
sudo systemctl start prefect-worker


We learned finally how modules are supposed to work (RTFM)
import .module is working from a mod directory

Tried to get docker working but then we realized what we really wanted was to run a commandline as a system... sound familiar? yeah its just like the server and the worker, duh.
