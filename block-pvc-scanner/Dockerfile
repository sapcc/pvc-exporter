FROM python:3.8.7

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY scanner.py ./

LABEL source_repository="https://github.com/sapcc/pvc-exporter"

CMD [ "python", "./scanner.py" ]
