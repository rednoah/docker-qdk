# QPKG Build Tools

Docker image for [QNAP Development Kit](https://github.com/qnap-dev/QDK).
- [`qbuild` (*Dockerfile*)](https://github.com/rednoah/docker-qdk/blob/master/Dockerfile)


## Usage

The [`qbuild`](https://github.com/qnap-dev/QDK) command-line tool:

```sh
docker run --rm -v "$PWD:/src" rednoah/qpkg-build --7zip
```


## GitHub Actions:
[![Build Docker](https://github.com/rednoah/docker-qdk/actions/workflows/docker.yml/badge.svg)](https://github.com/rednoah/docker-qdk/actions/workflows/docker.yml)
