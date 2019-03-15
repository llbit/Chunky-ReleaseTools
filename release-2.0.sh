# Starts a temporary container for experimenting with network access.
docker build -t chunkybuild .
docker run -it \
  --rm \
  --name chunky \
  -e RELEASE_GIT_BRANCH=flattening \
  -v "$PWD/private:/chunky/private" \
  chunkybuild
