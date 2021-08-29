FROM tiangolo/uvicorn-gunicorn-fastapi:latest
COPY ./app /app
COPY ./client/rclip /usr/local/bin
RUN mkdir /log
RUN pip install redis requests python-multipart
ENV ACCESS_LOG=/log/gunicorn-access.log
ENV ERROR_LOG=/log/gunicorn-error.log
ENV PORT=80
EXPOSE 80



