include *.conf


build:
	docker build -t docker-qdk .

help: build
	docker run --rm docker-qdk -help

extract:
	docker run -v $(PWD)/qpkg:/src --rm docker-qdk --extract '*.qpkg'

example: build
	rm -rv example
	docker run -v $(PWD):/src --rm docker-qdk --create-env example
	docker run -v $(PWD)/example:/src --rm docker-qdk .

pull:
	curl -o QDK.tar.gz -L "https://github.com/qnap-dev/QDK/archive/refs/tags/v${QDK_VERSION}.tar.gz"
	rm -rv QDK/*
	tar -xvf QDK.tar.gz -C QDK --strip-components=1
	rm -v QDK.tar.gz

clean:
	git reset --hard
	git pull
	git --no-pager log -1
