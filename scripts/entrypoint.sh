#!/bin/sh
git pull && \
  gpg --import release.key && \
  bash
