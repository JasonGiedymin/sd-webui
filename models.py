#!/usr/bin/env python3

import argparse
import sys
import os
import requests
import shutil
import subprocess
from time import sleep
from pathlib import Path
from os import path
import yaml

try:
    from huggingface_hub import hf_hub_url, hf_hub_download
except ModuleNotFoundError as ex:
    print(f'Did you source .venv? Error: {ex}')
    sys.exit()

VERBOSE=False

def checkDupes(yamlConfig):
    config_names = []
    config_items = []

    configDupeFound = False
    for idx, config in enumerate(yamlConfig['configs']):
        name = config['name']
        url = config['url']
        if url in config_items or name in config_names:
            print(f'config dupe found at entry #[{idx+1}]. Please correct.')
            configDupeFound = True
        else:
            if url == None or len(url) <= 0:
                msg = f'Empty url found for config entry #[{idx+1}]. Please correct.'
                sys.exit(msg)
            config_items.append(url)
            config_names.append(name)

    model_items = []
    modelDupeFound = False
    for idx, model in enumerate(yamlConfig['models']):
        repo_id = model['repo_id']
        filename = model['filename']
        
        if 'config' in model.keys():
            config_ref = model['config']
        else:
            config_ref = ''

        model_id = f'{repo_id}_{filename}'
        if model_id in model_items:
            print(f'model dupe found at entry #[{idx+1}]. Please correct.')
            modelDupeFound = True
        else:
            if len(config_ref) > 0 and config_ref not in config_names:
                msg = f'model referenced a non existant config "{config_ref}". Please correct it.'
                sys.exit(msg)

            model_items.append(model_id)

    # do this so we can get all the dupes, not just one
    if modelDupeFound and configDupeFound:
        msg = f'A duplicate entry in both the model and config lists was found. Please correct it.'
        sys.exit(msg)

    if modelDupeFound:
        msg = f'A duplicate entry in the model list was found. Please correct it.'
        sys.exit(msg)

    if configDupeFound:
        msg = f'A duplicate entry in the config list was found. Please correct it.'
        sys.exit(msg)

def checkConfig(yamlConfig):
    # required_keys = ['hf_token_rw', 'hf_token_ro', 'cache_dir', 'models']
    required_keys = ['hf_token_ro', 'cache_dir', 'models']
    for key in required_keys:
        if key not in yamlConfig.keys():
            msg = f'key: [{key}] is required, please supply it in models.yaml'
            sys.exit(msg)
    
    # check tokens
    if 'env.' in yamlConfig['hf_token_ro']:
        env_var_name_token_ro = yamlConfig['hf_token_ro'].split('.')[1]
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
        print(f'found: {yamlConfig["hf_token_ro"]}')
        sys.exit()
    
    if len(yamlConfig['cache_dir']) == 0:
        msg = 'You must supply a cache_dir in the models.yaml config file.'
        sys.exit(msg)
    
    if len(yamlConfig['models_dir']) == 0:
        msg = "You must supply a directory to be used for symlinks that will be volume'd with docker."
        sys.exit(msg)
    
    configs_dir = f"{yamlConfig['cache_dir']}/configs"
    if not path.exists(configs_dir):
        print(f'creating configs dir: {configs_dir}')
        Path(configs_dir).mkdir()
    
    checkDupes(yamlConfig)
    
    return token_ro

# will check if dirs exist and create them if necessary
def checkDirs(yamlConfig):
    cache_dir = yamlConfig['cache_dir']
    models_dir = yamlConfig['models_dir']

    for dir in [cache_dir, models_dir]:
        if not path.exists(f'./{dir}'):
            print(f'Please create the path ./{dir}, and re-run.')
            sys.exit()

def slugify(value, ext=''):
    slug = value
    slug = slug.replace('/', '_')
    slug = slug.replace('\\', '_')

    if len(ext) > 0:
        return f'{slug}.{ext}'

    return slug

def queryHub(cache_dir):
    command_result = subprocess.check_output([
        'huggingface-cli',
        'scan-cache',
        '--dir',
        cache_dir,
        '-v'
    ])

    return command_result.decode().split('\n')

def findRelativePath(path, cache_dir):
    dirs = path.split('/')
    for idx,dir in enumerate(dirs):
        if len(dir) > 0 and dir in cache_dir:
            return "/".join(dirs[idx:])

def queryModel(stdout_lines, model, cache_dir):
    repo_id = model['repo_id']
    c_repo_id = 0
    c_refs = 8
    c_local_path = 9
    
    for line in stdout_lines:
        columns = line.split()
        if len(columns) > (c_refs) and repo_id == columns[c_repo_id] and 'main' == columns[c_refs]:
            # don't return fully qualified paths, instead return
            # relative so that we can mount it with docker
            return findRelativePath(columns[c_local_path], cache_dir)
    
    msg = f'Could not find a model to link, repo_id: [{repo_id}]. Perhaps the download failed?'
    raise Exception(msg)

def findConfig(name, configs):
    for config in configs:
        if config['name'] == name:
            return config

def linkModel(model, configs, cache_dir, models_dir):
    # filename and slug
    enabled = model.get('enabled', True)
    ref_config = model.get('config', '')
    filename = model['filename']
    ext = filename.split('.')[-1]
    slug = slugify(model['repo_id'], ext)  # what we'll actually call the file rather than model.ckpt

    # data from output after querying hub
    stdout_lines = queryHub(cache_dir)
    model_local_path = queryModel(stdout_lines, model, cache_dir)
    full_model_path = f'./{model_local_path}/{filename}'
    model_dest = f'./{models_dir}/{slug}'  # where we'll symlink to later

    if len(ref_config) > 0:
        # don't assume, just get the extension
        config = findConfig(ref_config, configs)
        config_ext = config['url'].split('.')[-1]
        slug_config = slugify(model['repo_id'], config_ext)
        full_config_path = f'./{cache_dir}/configs/{config["url"].split("/")[-1]}'
        config_dest = f'./{models_dir}/{slug_config}'  # where we'll symlink to later
        
        # create model symlink
        if Path(model_dest).is_symlink():
            os.remove(model_dest)
        if enabled:
            os.symlink(full_model_path, model_dest)
        
        # create config symlink
        if Path(config_dest).is_symlink():
            os.remove(config_dest)        
        os.symlink(full_config_path, config_dest)

        if enabled:
            print(f'       link: [{full_model_path}] as [{slug}] and config of [{ref_config}] to {models_dir}')
            print(f'       link: [{ref_config}] as [{slug_config}] to {models_dir}')
    else:
        if Path(model_dest).is_symlink():
            os.remove(model_dest)
        if enabled:
            os.symlink(full_model_path, model_dest)
            print(f'       link: [{full_model_path}] as [{slug}] to {models_dir}')

# TODO: I don't like the filename
# for each model create a symlink to models
# if model['config'] was specified create a symlink for that to models, using the same name

def downloadModelConfig(config, token, cache_dir):
    name = config['name']
    url = config['url']
    filename = f'{cache_dir}/configs/{url.split("/")[-1]}'

    # try:
    response = requests.get(url, allow_redirects=True)
    if response.status_code not in [200]:
        msg = 'Error downloading from {url}, got status code: {response.status_code}, exiting ...'
        raise Exception(msg)
    else:
        file = Path(filename)
        file.write_bytes(response.content)

        print(f"""
     config: {name}
        url: {url}
   filename: {filename}
    """)

    # except Exception as exc:
    #     print(f'Error trying to download config {name}, error: {exc}')
    #     sys.exit()

def na(value, default='n/a'):
    if len(value) > 0:
        return value
    else:
        return default

def downloadModel(model, token, cache_dir):
    try:
        print(f"""
       model: {model["name"]}
     repo_id: {model["repo_id"]}
    filename: {model["filename"]}
      config: {model.get('config', 'n/a')}
     enabled: {model.get('enabled', True)}""")
        hf_hub_download(
            repo_id=model['repo_id'],
            filename=model['filename'],
            token=token,
            repo_type='model',
            cache_dir=cache_dir
        )
    except Exception as exc:
        print(f'Error trying to download model {model["name"]}, error: {exc}')
        sys.exit()

def download(yamlConfig, token, shouldLink):
    cache_dir = yamlConfig['cache_dir']
    models_dir = yamlConfig['models_dir']
    configs = yamlConfig['configs']
    models = yamlConfig['models']

    # download model configs first as we'll use them later for model linking
    for config in configs:
        downloadModelConfig(config, token, cache_dir)

    # download models
    for model in models:
        downloadModel(model, token, cache_dir)
        if shouldLink:
            linkModel(model, configs, cache_dir, models_dir)
    
    print("Finished downloading models.")

def cleanModels(yamlConfig):
    models_dir = yamlConfig['models_dir']

    if Path(models_dir).exists():
        print(f'First removing all contents in [{models_dir}] before recreating symlinks ...')
        shutil.rmtree(models_dir)
        sleep(1)
        os.mkdir(models_dir)

def loadConfig():
    with open("models.yaml", "r") as stream:
        try:
            yamlConfig = yaml.safe_load(stream)
            token = checkConfig(yamlConfig)
        except yaml.YAMLError as exc:
            sys.exit(exc)

    return yamlConfig, token

class Command(object):
    def __init__(self):
        parser = argparse.ArgumentParser(
            prog = 'models',
            description = 'Huggingface model download tool',
            epilog = '',
            add_help=True,
            usage='''models <command> [<args>]

Commands:
    download        Download models and configs, and link both.
    clean           Cleans up models and links by removing them
    check           Checks models.yaml config
''')
        
        parser.add_argument('command', help="command")
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            sys.exit()
        getattr(self, args.command)()
    
    def addVerbose(self, parser):
        parser.add_argument('-v', '--verbse', help='verbose mode', action='store_true')
    
    def addLinks(self, parser, help):
        parser.add_argument('-l', '--links', help=help, default=True, action='store_true')
    
    def download(self):
        parser = argparse.ArgumentParser(description='Download models')
        self.addVerbose(parser)
        self.addLinks(parser, help='links models')
        args = parser.parse_args(sys.argv[2:])

        # print(f'Running download, --links={args.links}')
        yamlConfig, token = loadConfig()
        checkDirs(yamlConfig)
        cleanModels(yamlConfig)  # we will remove the directory holding symlinks
        download(yamlConfig, token, args.links)
    
    def clean(self):
        parser = argparse.ArgumentParser(description='Clean models')
        self.addVerbose(parser)
        self.addLinks(parser, help='cleans links too')
        args = parser.parse_args(sys.argv[2:])
        yamlConfig, token = loadConfig()
        checkDirs(yamlConfig)
        cleanModels(yamlConfig)  # we will remove the directory holding symlinks
    
    def check(self):
        parser = argparse.ArgumentParser(description='Checking config ...')
        self.addVerbose(parser)
        self.addLinks(parser, help='cleans links too')
        args = parser.parse_args(sys.argv[2:])
        print(f'Running config check ... ')
        yamlConfig, token = loadConfig()
        print(f'Pass.')

def main():
    Command()

if __name__ == "__main__":
    main()