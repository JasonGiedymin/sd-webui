# FROM l1naforever/stable-diffusion-rocm:latest
FROM sd-base:1

COPY docker/entrypoint.sh /sd/entrypoint.sh

ENTRYPOINT /sd/entrypoint.sh