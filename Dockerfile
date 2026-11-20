FROM ubuntu:20.04

LABEL maintainer="Reinhard Pointner <rednoah@filebot.net>"


ENV LANG C.UTF-8

RUN apt-get update \
 && apt-get install -y build-essential bsdmainutils python openssl wget curl rsync p7zip-full \
 && rm -rvf /var/lib/apt/lists/*


COPY QDK /usr/local/QDK
COPY etc /etc
COPY opt /opt


RUN cd /usr/local/QDK/src && make \
 && ln -s /usr/bin/7z /usr/local/sbin/7z \
 && ln -s /usr/local/QDK/shared/bin/qbuild /usr/bin/qbuild \
 && ln -s /usr/local/QDK/shared/bin/qpkg_encrypt /usr/bin/qpkg_encrypt


WORKDIR /src


ENTRYPOINT ["/opt/bin/run"]
