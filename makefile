build:
	docker build -t docker-qdk .

help: build
	docker run --rm docker-qdk -help

example: build
	rm -rvf example
	docker run -v $(PWD):/src --rm docker-qdk --create-env example
	docker run -v $(PWD)/example:/src --rm docker-qdk .
