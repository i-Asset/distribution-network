#!/usr/bin/env bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)

export TAGNAME="v0.1"

###################### build, run and push ##########################
echo
echo
echo "build and push full image with tag $TAGNAME."
docker-compose build

export IMG_ID=$(docker image ls | grep iassetplatform/distribution-network | head -1 | awk '{print $3}')
echo "push image with ID $IMG_ID and Tag '$TAGNAME'."

docker tag $IMG_ID iassetplatform/distribution-network:$TAGNAME
docker push iassetplatform/distribution-network:$TAGNAME
