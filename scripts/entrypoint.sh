#!/bin/bash

set -e

cp private/gradle.properties ~/.gradle/
git pull
gpg --import private/release.key

echo "Pre-release checklist:"
echo "    * Update release notes (& check for typos)."
echo "    * Update ChangeLog (check for typos)."
echo "    * Commit all final changes in git."
echo "    * (git checkout <BRANCH> to release non-trunk build)"
echo "Run './shipity.py <VERSION>' when ready"

bash
