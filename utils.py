import json
import os
from typing import List, Tuple

def encrypt(message:str, key=None) -> str:
    # return(hash(key)%ord(i) for i in message) 
    return message

def decrypt(message:str, key=None) -> str:
    return message

def load_users_from_json(filename: str = "users.json") -> List[Tuple[str, str]]:
    """load legal users from JSON file"""
    try:
        # get dir
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(current_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"user file {filename} not found")

        with open(filepath, "r", encoding="utf-8") as f:
            users_data = json.load(f)

        # validate and parse
        valid_users = []
        for user in users_data:
            if "username" in user and "password" in user:
                valid_users.append((user["username"], user["password"]))
            else:
                raise ValueError("JSON format err: username or password absent")
        
        return valid_users
    
    except json.JSONDecodeError:
        raise ValueError("err parsing JSON file")
    except Exception as e:
        raise RuntimeError(f"err loading user file: {str(e)}")