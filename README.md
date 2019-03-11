# Chunky Release Tools

Scripts to automate the Chunky release process with a Docker container.

## One Time Setup

The `./private/` directory should be populated with
gradle.properties and release.key.

    mkdir private
    cp ~/.gradle/gradle.properties private
    gpg --export-secret-keys <KEYID> > private/release.key


## Release Process

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

Wine and NSIS are used to build a Windows installer.


[1]: https://bitbucket.org/infinitekind/appbundler/src
