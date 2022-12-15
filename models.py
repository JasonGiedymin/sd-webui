#!/usr/bin/env python3

from huggingface_hub import hf_hub_url, hf_hub_download
import joblib
import sys
import yaml
import os

def checkConfig(models_config):
    # required_keys = ['hf_token_rw', 'hf_token_ro', 'cache_dir', 'models']
    required_keys = ['hf_token_ro', 'cache_dir', 'models']
    for key in required_keys:
        if key not in models_config.keys():
            msg = f'key: [{key}] is required, please supply it in models.yaml'
            sys.exit(msg)
    
    # check tokens
    if 'env.' in models_config['hf_token_ro']:
        env_var_name_token_ro = models_config['hf_token_ro'].split('.')[1]
        if env_var_name_token_ro in os.environ.keys():  # we have a key
            token_ro = os.environ[env_var_name_token_ro]
            if len(token_ro) <= 0:  # key has an actual value
                msg = f'You must supply the env variable {env_var_name_token_ro}'
                sys.exit(msg)
        else:
            msg = f"Can't find env var {env_var_name_token_ro}, please supply it."
            sys.exit(msg)
    else:  # no env.
        print('you may have supplied the full token, right now we only use the format "env.ENV_VAR_NAME"')
        print(f'found: {models_config["hf_token_ro"]}')
        sys.exit()
    
    if len(models_config['cache_dir']) == 0:
        msg = 'You must supply a cache_dir in the models.yaml config file.'
        sys.exit(msg)
    
    return token_ro, models_config['cache_dir']

def downloadModel(model, token, cache_dir):
    try:
        print(f"""
    model: {model["name"]}
    repo_id: {model["repo_id"]}
    filename: {model["filename"]}
        """)
        model = joblib.load(
            hf_hub_download(
                repo_id=model['repo_id'],
                filename=model['filename'],
                token=token,
                repo_type='model',
                cache_dir=cache_dir
            )
        )
    except Exception as exc:
        sys.exit(exc)

def start():
    with open("models.yaml", "r") as stream:
        try:
            models_config = yaml.safe_load(stream)
            token, cache_dir = checkConfig(models_config)
        except yaml.YAMLError as exc:
            sys.exit(exc)

    print(f'token: {token}')

    for model in models_config['models']:
        downloadModel(model, token, cache_dir)
    
    sys.exit("Done.")

start()
