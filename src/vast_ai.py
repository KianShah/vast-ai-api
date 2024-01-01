import hashlib
import time
from typing import Dict, Literal
import pandas as pd
import requests
from datetime import date

# https://vast.ai/
class VastAPIHelper:
    BASE_URL = 'https://console.vast.ai/api/v0'

    def __init__(self, API_KEY: str):
        self.API_KEY = API_KEY
        
    def list_available_instances(self, verified: bool = True) -> pd.DataFrame:
        query = {
            "verified": {'eq': verified},
            "external": {'eq': True},
            "rentable": {'eq': True},
            "order": [["dph", "asc"]]
        }

        res = requests.get(f"{self.BASE_URL}/bundles", json={'q': query})
        res.raise_for_status()
        df = pd.DataFrame.from_records(res.json()['offers'])
        print(f"Recieved {len(df)} results")
        df.rename({
            "gpu_name": "name",
            "dph_total": "$/hr",
            "gpu_ram": "vram",
            "cpu_ram": "ram",
            "verified": "is_secure",
            "inet_up": "inet_upload",
            "inet_up_cost": "inet_upload_cost",
            "inet_down": "inet_download",
            "inet_down_cost": "inet_download_cost",
            "geolocation": 'region',
            "disk_space": "disk_space_available"
        }, inplace=True, axis=1)
        df["vram"] = df["vram"].apply(lambda x: x//1000)

    def list_current_instances(self) -> pd.DataFrame:
        res = requests.get(f"{self.BASE_URL}/instances",
                           params={"owner": "me", "api_key": self.API_KEY})
        res.raise_for_status()
        return pd.DataFrame.from_records(res.json()['instances'])

    def _set_instance_state(self, instance_id: str, method: Literal["PUT", "DELETE"], state: str = None) -> None:
        if method == "PUT":
            res = requests.put(f"{self.BASE_URL}/instances/{instance_id}/",
                               params={"api_key": self.API_KEY}, json={'state': state})
        elif method == "DELETE":
            res = requests.delete(
                f"{self.BASE_URL}/instances/{instance_id}/", params={"api_key": self.API_KEY})
        else:
            raise Exception("Unkown Method used")
        res.raise_for_status()
        res = res.json()
        if 'msg' in res:
            raise Exception(res['msg'])

    def launch_instance(self, 
                        instance_id: str, 
                        docker_image_name: str = "tensorflow/tensorflow:latest-gpu", 
                        name: str = None, 
                        env: Dict = None, 
                        disk_size: int = 50, 
                        bid_price_per_machine: float = None) -> None:
        payload = {
            "client_id": "me",
            "image": docker_image_name,
            # "env": parse_env(args.env), # env variables and port mapping options, surround with ''
            "price": bid_price_per_machine, # $/hr
            "disk": disk_size,
            "label": name,
            "runtype": "jupyter_direc ssh_direc ssh_proxy", # Allowed runtype strings are [jupyter_direc, ssh_direc, ssh_proxy, jupyter_proxy]
            # "image_login": args.login,  # Custom login args for use of a docker image in a private repo
            "use_jupyter_lab": True,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        res = requests.put(f"{self.BASE_URL}/asks/{instance_id}/", params={"api_key": self.API_KEY}, json=payload)
        res.raise_for_status()
        
    def change_bid(self, instance_id: str, price: float) -> None:
        res = requests.put(f"{self.BASE_URL}/instances/bid_price/{instance_id}/", {"client_id": "me", "price": price})
        res.raise_for_status()
        
    def get_instance(self, instance_id: str) -> pd.DataFrame:
        raise NotImplementedError("Not possible to get instance because the instance ID actually changes after creating the instance. Weird I know.")

    def start_instance(self, instance_id: str) -> pd.DataFrame:
        self._set_instance_state(instance_id, 'PUT', 'running')

    def stop_instance(self, instance_id: str) -> None:
        self._set_instance_state(instance_id, 'PUT', 'stopped')
            
    def reboot_instance(self, instance_id: str) -> None:
        self.stop_instance(instance_id)
        self.start_instance(instance_id)
        
    def label_instance(self, instance_id: str, label: str) -> None:
        res = requests.put(f"{self.BASE_URL}/instances/{instance_id}/", {"label": label})
        res.raise_for_status()

    def delete_instance(self, instance_id: str) -> None:
        self._set_instance_state(instance_id, 'PUT', 'stopped')
        self._set_instance_state(instance_id, 'DELETE')
        
    def get_instance_logs(self, instance_id: str, tail: int = 1000) -> str:
        res = requests.put(f"{self.BASE_URL}/instances/request_logs/{instance_id}/", {"tail": tail})
        res.raise_for_status()
        private_key = (self.API_KEY + str(instance_id)).encode('utf-8')
        api_key_id_h = hashlib.md5(private_key).hexdigest()
        s3_url = f"https://s3.amazonaws.com/vast.ai/instance_logs/{api_key_id_h}.log"
        for _ in range(30):
            r = requests.get(s3_url)
            if (r.status_code == 200):
                return r.text
            print(f"Waiting on logs for instance {instance_id} fetching from {s3_url}")
            time.sleep(0.5)

        
    """
        Host actions
    """
        
    def show_hosted_machines(self) -> None:
        res = requests.get(f"{self.BASE_URL}/machines", {'owner': 'me'})
        res.raise_for_status()
        return res
    

    def list_machine_for_rent(self, price_per_gpu: float, storage_price: float, price_inet_up: float, price_inet_down: float, min_gpus: int, end_date: date, discount_rate: float = 0.4):
        ...  # TODO
        
    def unlist_machine_for_rent(self, instance_id: str) -> None:
        res = requests.delete(f"{self.BASE_URL}/machines/{instance_id}/asks/")
        res.raise_for_status()
        