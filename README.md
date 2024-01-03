# A low-level API for Vast.ai
 
 This project is not intended to replace the open-source [vast.ai library](https://github.com/vast-ai/vast-python) but rather to complement it for those who want to have an easy-to-use API to build their own projects. The goal of this project is not to re-implement every functionality in the original library but to simplify it for future developers and end users.
 
 It also integrates [pandas](https://pandas.pydata.org/) dataframes for easier data manipulation.


## Installation/Setup instructions
vast-ai-api is available on PyPi:

```bash
$ pip install vast-ai-api
```
or
```bash
$ poetry add vast-ai-api
```

Export your [Vast-AI API key](https://vast.ai/docs/account/account-settings?query=change-ssh-key#change-api-key):

```bash
$ export VAST_AI_API_KEY=<YOUR_API_KEY_HERE>
```
After you reserve an instance, in order to change its state or interact with it in any way, you will need to setup an [SSH key](https://vast.ai/docs/account/account-settings?query=change-ssh-key#change-ssh-key) on Vast.ai.

## Usage
Initializing the API Helper:

```python
import pandas as pd
from vast_ai_api import VastAPIHelper

api = VastAPIHelper()
```
List all instances available to be rented
```python
instances: pd.DataFrame = api.list_available_instances()
```

Pick an instance from the list and reserve it using its instance_id
```python
instance: pd.Series = instances.iloc[50]
instance_id = instance['id']
machine_id = instance['machine_id']  # Needed after reserving
api.launch_instance(instance_id)
```

Instance is now launched and starting up with default parameters
```python
launched_instances = api.list_current_instances()
newly_launched_instance = launched_instances[launched_instances['machine_id'] == machine_id]
```

Note that the `instance_id` that we got before reserving the instance changes after reservation. Instead, we have to use the `machine_id` to find the instance again and get its new id

```python
new_instance_id = newly_launched_instance['id']
```

Now we can perform actions on this launched instance:

```python
api.stop_instance(new_instance_id)
api.start_instance(new_instance_id)
api.reboot_instance(new_instance_id)  # Equivalent to stopping and starting the instance

api.get_instance_logs(new_instance_id)
```

### Connecting through SSH
Prerequisites: You must have added your private key to your ssh-agent, as paramiko will, by default, use those keys to connect to the instance.

In addition, you must have initialized the instance as `api.launch_instance(instance_id, use_jupyter_lab=False)`

You can connect to the instance in 2 ways: with or without port forwarding. Port forwarding is recommended as it allows you to stay anonymous when connecting to the gpu provider:
```python
client = api.connect_ssh(new_instance_id)
stdin, stdout, stderr = client.exec_command(<your_command_here>)
print(stdout.readlines())
```
Forwarding port 8080:
```python
client = api.connect_ssh(new_instance_id, port_forwarding=(8080, 8080))
```
Alternatively, you can connect directly via the command line by reading the necessary host and port of the machine:
```python
ssh_host = newly_launched_instance['ssh_host']
ssh_port = newly_launched_instance['ssh_port']
```
and then use `ssh` to connect your terminal to the instance:
```bash
$ ssh -p ${ssh_port} ${ssh_host} -L 8080:localhost:8080
```
