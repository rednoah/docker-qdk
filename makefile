help:
	docker build --rm -t docker-qdk .
	docker run -it -v ${PWD}:/src docker-qdk -help
