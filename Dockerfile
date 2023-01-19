# Docker can cache layers heavily and you'll find that re-sourcing
# coexists just fine with replayed cache layers, it saves a lot of time
FROM alpine/git:latest AS builder
WORKDIR /opt
RUN git clone --depth 1 https://github.com/AUTOMATIC1111/stable-diffusion-webui
WORKDIR /opt/stable-diffusion-webui

FROM rocm/pytorch:latest
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    REQS_FILE='requirements.txt'

COPY --from=builder /opt/stable-diffusion-webui /sd
WORKDIR /sd

SHELL ["/bin/bash", "-c"]

# Base layer
RUN apt-get update && \
    apt-get install -y libglib2.0-0 wget python3 python3-venv python3-dev \
                       git build-essential autoconf libtool pkg-config \
                       make unzip autoconf libsm6 libxext6 ffmpeg vim && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/* && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    python3 -m pip install --upgrade pip wheel

#
# Warning: changes below here will require you to run 'run.sh reset'
#

# layered so we can cache this result, this op takes a long time
# (also source again for consistency)
RUN source venv/bin/activate && \
    python3 -m pip install numpy --pre torch torchvision torchaudio --force-reinstall --index-url https://download.pytorch.org/whl/nightly/cu117

# layered so we can cache this result (also source again for consistency)
RUN apt-get update && \
    apt-get install -y libglib2.0-0 wget && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/* && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    python3 -m pip install --upgrade ninja && \
    python3 -m pip install --upgrade torch torchvision --extra-index-url https://download.pytorch.org/whl/rocm5.2
    
# layered requirements, we can change these and build quickly from the above being cached
# (also source again for consistency)
RUN source venv/bin/activate && \
    python3 -m pip install -r requirements.txt

COPY docker/entrypoint.sh /sd/entrypoint.sh

ENTRYPOINT /sd/entrypoint.sh
