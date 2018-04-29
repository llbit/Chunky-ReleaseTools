# Chunky Release Tools

Scripts to automate the Chunky release process with a Docker container.

## Release Process

One time setup (export release key):

    gpg --export-secret-keys <KEYID> > private/release.key


Add release notes:

    vi data/release_notes-<VERSION>.txt


Start the container:

    ./start-docker.sh
    # ./shipit.py <VERSION>


## Tools Used

Docker is used to create a Linux container for clean reproducible build workflow.

Launchpadlib is a Python library used to work with the Launchpad API.

PRAW is used to post relase threads on Reddit.

Appbundler ([bitbucket.org/infinitekind/appbundler][1]) is used to build the Mac App.


[1]: https://bitbucket.org/infinitekind/appbundler/src
