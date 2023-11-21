FROM python:3.9
ENV PYTHONUNBUFFERED 1
ENV PYTHONWARNINGS "ignore:Unverified HTTPS request"
ENV FLASK_APP flaskr
RUN mkdir /code
WORKDIR /code
COPY requirements.txt /code/
COPY . /code/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

#Debug
# CMD python run.py

# Prod
CMD gunicorn --bind 0.0.0.0:5000 -w 1 run:gunicorn_app
