FROM nginx:latest

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends python python-pip python-dev

RUN pip install cloudant
RUN apt-get install -y --no-install-recommends build-essential
RUN apt-get install -y --no-install-recommends supervisor
RUN pip install uwsgi
RUN apt-get install -y --no-install-recommends python-numpy

RUN mkdir -p /home/uwsgi
RUN mkdir -p /etc/uwsgi/vassals
RUN mkdir /database_attachments

VOLUME [ "/var/log/supervisor", "/database_attachments" ]

COPY ./nginx.conf.in /nginx.conf.in
COPY ./uwsgi.conf /etc/init/uwsgi.conf
COPY ./docker-entrypoint.sh /entrypoint.sh
COPY ./wsgi.ini /etc/uwsgi/vassals/wsgi.ini
COPY ./handle_req.py /home/uwsgi/handle_req.py
COPY ./supervisor-app.conf /etc/supervisor/conf.d/supervisor-app.conf

EXPOSE 80
EXPOSE 5984

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx"]
