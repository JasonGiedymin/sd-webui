# Setup

## TLDR

`python3 -m venv .venv`

Setup packages and run

```shell
source .venv/bin/activate

pip install -r requirements.txt

# new packages? Run below
# pip freeze > requirements.txt

# supply env

./download.sh
./build.sh

deactivate
exit
```

## Step 1 - venv

Create and source a virtual env

Create it like so:

```shell
python3 -m venv .venv
```

Activate it and install libs like so:
```shell
source .venv/bin/activate

pip install -r requirements.txt
```

## Step 2 - Setup env

Copy and supply tokens in in the `env` file.

```shell
cp env.sample env
```

## Step 3 - Download Models

Models are auto downloaded from build but you can run the download manually.

```shell
./download.sh
```

## Step 4 - Build

```shell
./build.sh
```
