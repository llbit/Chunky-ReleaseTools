FROM debian

RUN dpkg --add-architecture i386 && \
	apt-get update && \
	apt-get install -y \
		ant \
		curl \
		genisoimage \
		git \
		locales \
		openjdk-8-jdk-headless \
		openjfx \
		python \
		python-pip \
		pinentry-tty \
		vim \
		wine32 \
		zip

# Get Python packages:
RUN pip install praw==5.4.0 launchpadlib==1.10.6

WORKDIR /root

# GnuPG configuration:
COPY conf/gpg-agent.conf .gnupg/gpg-agent.conf
RUN chmod -R 600 .gnupg

# Get NSIS:
RUN curl -L https://sourceforge.net/projects/nsis/files/NSIS%203/3.03/nsis-3.03.zip/download \
		> nsis-3.03.zip && \
	unzip nsis-3.03.zip && \
	rm nsis-3.03.zip

COPY conf/gitconfig .gitconfig

# Get Chunky and Gradle:
RUN git clone https://github.com/llbit/chunky.git /chunky && \
	/chunky/gradlew -version

WORKDIR /chunky

# This bit is taken from https://stackoverflow.com/a/28406007/1250278
# I don't know why the sed command is needed, and couldn't easily find an
# explanation, but it seems to not work without it.
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Copy release scripts and data:
COPY scripts .
COPY data .
COPY tools tools

CMD ["./entrypoint.sh"]
