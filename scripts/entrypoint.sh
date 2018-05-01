#!/bin/bash

set -e

git pull
gpg --import release.key

echo "Pre-release checklist:"
echo "    * Update release notes (& check for typos)."
echo "    * Update ChangeLog (check for typos)."
echo "    * Commit all final changes in git."
echo "Run './shipity.py <VERSION>' when ready"

bash
