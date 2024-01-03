# A clean scriptable library for Vast.ai
 
 This project is not intended to replace the open-source [vast.ai library](https://github.com/vast-ai/vast-python) but rather to complement it for those who want to have an easy-to-use API to build their own projects. 
 
 It also integrates [pandas](https://pandas.pydata.org/) dataframes for easier data manipulation.


## Installation instructions
vast-ai-api is available on PyPi:

```bash
$ pip install vast-ai-api
```
or
```bash
$ poetry add vast-ai-api
```
## Usage
Firstly, ensure you export your [Vast-AI API key](https://vast.ai/docs/account/account-settings?query=change-ssh-key#change-api-key):

```bash
$ export VAST_AI_API_KEY=<YOUR_API_KEY_HERE>
```
After you reserve an instance, in order to change its state or interact with it in any way, you need to setup an [SSH key](https://vast.ai/docs/account/account-settings?query=change-ssh-key#change-ssh-key) on Vast.ai.

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