FROM tiangolo/uvicorn-gunicorn-fastapi:latest
COPY ./app /app
RUN mkdir /logs
RUN pip install redis requests python-multipart
ENV ACCESS_LOG=/logs/gunicorn-access.log
ENV ERROR_LOG=/logs/gunicorn-error.log
ENV PORT=80
EXPOSE 80
