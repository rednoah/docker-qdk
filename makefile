build:
	docker build --rm -t docker-qdk .
	docker run -it docker-qdk -help
