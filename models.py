#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
import requests
from requests.exceptions import HTTPError
import shutil
import subprocess
import sys
from tqdm import tqdm
from time import sleep
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

    raw_names = []
    raw_items = []
    rawModelDupeFound = False
    for idx, model in enumerate(yamlConfig['raw_models']):
        name = model['name']
        url = model['url']
        filename = model['filename']
        if url in raw_items or name in raw_names:
            print(f'raw model dupe found at entry #[{idx+1}]. Please correct.')
            rawModelDupeFound = True
        else:
            if url == None or len(url) <= 0:
                msg = f'Empty url found for raw model entry #[{idx+1}]. Please correct.'
                sys.exit(msg)
            if filename == None or len(filename) <= 0:
                msg = f'Empty filename found for entry #[{idx+1}], you must specify a filename to write as.'
                sys.exit(msg)

            raw_items.append(url)
            raw_names.append(name)

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
    
    if rawModelDupeFound:
        msg = f'A duplicate entry in the raw model list was found. Please correct it.'
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
    
    raw_models_dir = f"{yamlConfig['cache_dir']}/raw_models"
    if not path.exists(raw_models_dir):
        print(f'creating raw models dir: {raw_models_dir}')
        Path(raw_models_dir).mkdir()
    
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
    # debounce query by 0.5 seconds
    # sleep(1)
    repo_id = model['repo_id']
    c_repo_id = 0
    c_refs = 8
    c_local_path = 9
    
    for line in stdout_lines:
        columns = line.split()
        
        if len(columns) < (c_refs):
            continue

        if repo_id != columns[c_repo_id]:
            continue

        # the difference is '1 second ago' (len=3) and 'a few seconds ago' (len=4), so add 1
        # don't return fully qualified paths, instead return
        # relative so that we can mount it with docker
        if len(columns) > c_refs:
            if 'main' == columns[c_refs]:
                return findRelativePath(columns[c_local_path], cache_dir)
        if len(columns) > c_refs+1:
            if 'main' == columns[c_refs+1]:
                return findRelativePath(columns[c_local_path+1], cache_dir)
    
    msg = f'Could not find a model to link, repo_id: [{repo_id}]. Perhaps the download failed?'
    raise Exception(msg)

def findConfig(name, configs):
    for config in configs:
        if config['name'] == name:
            return config

def linkRawModel(model, configs, cache_dir, models_dir):
    # filename and slug
    enabled = model.get('enabled', True)
    ref_config = model.get('config', '')
    filename = model['filename']
    full_model_path = f'./{cache_dir}/{filename}'
    model_dest = f'./{models_dir}/{filename}'  # where we'll symlink to later

    if len(ref_config) > 0:
        # don't assume, just get the extension
        config = findConfig(ref_config, configs)
        config_ext = config['url'].split('.')[-1]
        slug_config = slugify(filename, config_ext)
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
            print(f'       link: [{full_model_path}] as [{models_dir}/{filename}] with config of [{ref_config}]')
            print(f'       link: [{ref_config}] as [{models_dir}/{slug_config}]')
    else:
        if Path(model_dest).is_symlink():
            os.remove(model_dest)
        if enabled:
            os.symlink(full_model_path, model_dest)
            print(f'       link: [{full_model_path}] as [{models_dir}/{filename}]')

def queryModelOnHub(model, cache_dir):
    '''
    Due to slow disk or very busy IO, this pause may help.
    Otherwise things will run fine and fast.
    '''
    tries = 0
    limit = 10
    wait_time = 30  # seconds
    while tries < limit:
        # data from output after querying hub
        stdout_lines = queryHub(cache_dir)
        # model_local_path = queryModel(stdout_lines, model, cache_dir)
        model_local_path = queryModel(stdout_lines, model, cache_dir)
        if model_local_path == None:
            tries = tries + 1
            print('!? Could not yet find model in question, running query again in {wait_time} second(s) ... !?')
            print(f'\n\n\n{stdout_lines}\n\n\n')
            sleep(wait_time)
        else:
            return model_local_path

def linkModel(model, configs, cache_dir, models_dir):
    # filename and slug
    tries=0
    enabled = model.get('enabled', True)
    ref_config = model.get('config', '')
    filename = model['filename']
    ext = filename.split('.')[-1]
    slug = slugify(model['repo_id'], ext)  # what we'll actually call the file rather than model.ckpt

    model_local_path = queryModelOnHub(model, cache_dir)

    if model_local_path is None:
        msg = f'error with model_local_path, found None ...'
        print(msg)
        sys.exit(msg)

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
            print(f'       link: [{full_model_path}] as [{models_dir}/{slug}] with config of [{ref_config}]')
            print(f'       link: [{ref_config}] as [{models_dir}/{slug_config}]')
    else:
        if Path(model_dest).is_symlink():
            os.remove(model_dest)
        if enabled:
            os.symlink(full_model_path, model_dest)
            print(f'       link: [{full_model_path}] as [{models_dir}/{slug}]')

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

def downloadRawEmbedding(raw_item, dest_dir):
    name = raw_item['name']
    url = raw_item['url']
    filename = f'{dest_dir}/{raw_item["filename"]}'

    try:
        if Path(filename).exists():
            print(f'  Raw model: {filename} already exists, not overwriting. Delete and re-run if you want to update. Moving on ...')
            return

        print(f'\nDownloading: {url} as {filename} ...')
        with requests.get(url, stream=True, allow_redirects=True) as r:
            total_size_in_bytes= int(r.headers.get('content-length', 0))
            block_size = 8192 #or 1024
            progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
            r.raise_for_status()
            with open(filename, 'wb') as file:
                for chunk in r.iter_content(chunk_size=8192): 
                    progress_bar.update(len(chunk))
                    file.write(chunk)
            print(f"""
      embed: {name}
        url: {url}
   filename: {filename}
    """)
        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            msg = f"Error while attempting to download url {url}"
            sys.exit(msg)
    except HTTPError as exc:
        code = exc.response.status_code
        if code in [429, 500, 502, 503, 504]:
            # retry after n seconds
            sleep(10)
        raise

def downloadRawModel(raw_model, cache_dir):
    name = raw_model['name']
    url = raw_model['url']
    filename = f'{cache_dir}/raw_models/{raw_model["filename"]}'

    try:
        if Path(filename).exists():
            print(f'  Raw model: {filename} already exists, not overwriting. Delete and re-run if you want to update. Moving on ...')
            return

        print(f'\nDownloading: {url} as {filename} ...')
        with requests.get(url, stream=True, allow_redirects=True) as r:
            total_size_in_bytes= int(r.headers.get('content-length', 0))
            block_size = 8192 #or 1024
            progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
            r.raise_for_status()
            with open(filename, 'wb') as file:
                for chunk in r.iter_content(chunk_size=8192): 
                    progress_bar.update(len(chunk))
                    file.write(chunk)
            print(f"""
     config: {name}
        url: {url}
   filename: {filename}
    """)
        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            msg = f"Error while attempting to download url {url}"
            sys.exit(msg)
    except HTTPError as exc:
        code = exc.response.status_code
        if code in [429, 500, 502, 503, 504]:
            # retry after n seconds
            sleep(10)
        raise

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

def handleConfigs(configs, token, cache_dir):
    # download model configs first as we'll use them later for model linking
    for config in configs:
        downloadModelConfig(config, token, cache_dir)

def download(yamlConfig, token, shouldLink):
    # dirs
    cache_dir = yamlConfig['cache_dir']
    raw_model_cache_dir = f'{cache_dir}/raw_models'
    models_dir = yamlConfig['models_dir']
    embeddings_dir = f'./volumes/embeddings/'

    # keys
    configs = yamlConfig['configs']
    models = yamlConfig['models']
    raw_models = yamlConfig['raw_models']
    raw_embeddings = yamlConfig['raw_embeddings']

    # download model configs first as we'll use them later for model linking
    for config in configs:
        downloadModelConfig(config, token, cache_dir)
    
    for raw_model in raw_models:
        downloadRawModel(raw_model, cache_dir)
        if shouldLink:
            linkRawModel(raw_model, configs, raw_model_cache_dir, models_dir)

    # download models
    for model in models:
        downloadModel(model, token, cache_dir)
        if shouldLink:
            linkModel(model, configs, cache_dir, models_dir)
    
    # download embeddings
    for raw_embedding in raw_embeddings:
        downloadRawEmbedding(raw_embedding, embeddings_dir)
    
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