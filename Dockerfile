FROM ubuntu:18.04

MAINTAINER Reinhard Pointner <rednoah@filebot.net>


ENV LANG C.UTF-8

RUN apt-get update \
 && apt-get install -y build-essential bsdmainutils python openssl wget curl rsync p7zip-full \
 && rm -rvf /var/lib/apt/lists/*


COPY QDK /usr/share/QDK
COPY qdk.conf /etc/config/qdk.conf


RUN cd /usr/share/QDK/src && make \
 && ln -s /usr/bin/7z /usr/local/sbin/7z \
 && ln -s /usr/share/QDK/shared/bin/qbuild /usr/bin/qbuild \
 && ln -s /usr/share/QDK/shared/bin/qpkg_encrypt /usr/bin/qpkg_encrypt


VOLUME /src
WORKDIR /src


ENTRYPOINT ["qbuild"]
