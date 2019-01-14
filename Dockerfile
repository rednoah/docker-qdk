FROM ubuntu:latest

MAINTAINER Reinhard Pointner <rednoah@filebot.net>


RUN apt-get update \
 && apt-get install -y build-essential python rsync p7zip-full \
 && rm -rvf /var/lib/apt/lists/*


ADD QDK /usr/local/QDK
ADD qdk.conf /etc/config/qdk.conf


RUN cd /usr/local/QDK/src && make \
 && ln -s /usr/bin/7z /usr/local/sbin/7z \
 && ln -s /usr/local/QDK/shared/bin/qbuild /usr/bin/qbuild \
 && ln -s /usr/local/QDK/shared/bin/qpkg_encrypt /usr/bin/qpkg_encrypt


WORKDIR /src


ENTRYPOINT ["qbuild"]
