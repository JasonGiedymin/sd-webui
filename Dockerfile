# FROM l1naforever/stable-diffusion-rocm:latest
FROM sd-base:1

# xformers doesn't fully work on AMD yet
# RUN pip install -U pip && \
#     pip install -U ninja && \
#     pip install -v -U git+https://github.com/facebookresearch/xformers.git@main#egg=xformers && \
#     pip install -r requirements.txt && \
#     pip freeze | grep xformers

RUN pip install -U pip && \
    pip install -r requirements.txt

COPY docker/entrypoint.sh /sd/entrypoint.sh

ENTRYPOINT /sd/entrypoint.sh