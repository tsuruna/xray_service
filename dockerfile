FROM python:3.7.3-alpine

ENV APP_DIR=./

EXPOSE 8080

# App configuration
WORKDIR ${APP_DIR}
RUN mkdir -p ${APP_DIR} && mkdir ${APP_DIR}/uploads && chmod -R a+rw ${APP_DIR}/uploads
COPY requirements.txt ${APP_DIR}/

RUN pip install --upgrade pip && \
	pip install -U -r requirements.txt

COPY *.py ${APP_DIR}/
ENTRYPOINT ["python"]
CMD ["uploader.py"]