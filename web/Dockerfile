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
#Debug
# change run app to point to debug app
CMD python run.py

# Prod
# change run app to point to production app
#CMD gunicorn --bind 0.0.0.0:5000 -w 1 run:app
