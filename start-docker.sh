# Starts a temporary container for experimenting with network access.
docker build -t chunkybuild .
docker run -it \
  --rm \
  --name chunky \
  -v chunky_private:/chunky/private \
  chunkybuild
