FROM python:3.9
ENV PYTHONUNBUFFERED 1
ENV PYTHONWARNINGS "ignore:Unverified HTTPS request"
ENV FLASK_APP flaskr
RUN mkdir /code
WORKDIR /code
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /code/
EXPOSE 5000
CMD python run.py
#CMD gunicorn --bind 0.0.0.0:5000 -w 3 run:app