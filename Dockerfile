FROM tiangolo/uvicorn-gunicorn-fastapi:latest
COPY ./app /app
COPY ./dist/rclip-latest.tar.gz /dist/rclip-latest.tar.gz
RUN mkdir /log
RUN pip install redis requests python-multipart
RUN pip install /dist/rclip-latest.tar.gz
ENV ACCESS_LOG=/log/gunicorn-access.log
ENV ERROR_LOG=/log/gunicorn-error.log
ENV PORT=80
EXPOSE 80



