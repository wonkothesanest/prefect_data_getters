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

What are the ETL steps? 
Raw, vector store (searchable), processed, query output
Could use Rabbit MQ for after loading a document add it to the rabbit


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


For installation you need to run pip install -e . from the base directory (where setup.py is). 

TODO List:
* Make slab auto backup every week
* Make deployments use the prefect command line interface instead of services. or prefect.yaml
* apply labels to gmail messages
* make a robot secratary to make mornings more efficient
* think about and commit to best structure.
* decide between n8n and prefect


TODONE: 
* Make gmail backup faster
* Make Gmail backup more frequent (no dependence on thunderbird?)