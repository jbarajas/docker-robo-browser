FROM ubuntu:14.04

MAINTAINER hardlyhaki@gmail.com

RUN sudo apt-get update && sudo apt-get -y upgrade

# Add the PostgreSQL PGP key to verify their Debian packages.
# It should be the same key as https://www.postgresql.org/media/keys/ACCC4CF8.asc
RUN apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8

# Add PostgreSQL's repository. It contains the most recent stable release
#     of PostgreSQL, ``9.3``.
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main" > /etc/apt/sources.list.d/pgdg.list

RUN sudo apt-get install -y \
	apache2 \
	git \
	openssh-server \
	postgresql-9.3 \
	postgresql-client-9.3 \
	postgresql-contrib-9.3 \
	python \
	python-pip \
	python3 \
	python3-pip \
	python-psycopg2 \
	python-software-properties \
	software-properties-common \
	supervisor \
	unzip \
	wget \
	xvfb

# DEV - Tools to be removed at publication
RUN sudo apt-get install -y \
	vim \
	tree

# Run the rest of the commands as the ``postgres`` user created by the ``postgres-9.3`` package when it was ``apt-get installed``
USER postgres

# Create a PostgreSQL role named ``docker`` with ``docker`` as the password and
# then create a database `docker` owned by the ``docker`` role.
# Note: here we use ``&&\`` to run commands one after the other - the ``\``
#       allows the RUN command to span multiple lines.
RUN    /etc/init.d/postgresql start &&\
    psql --command "CREATE USER docker WITH SUPERUSER PASSWORD 'docker';" &&\
    createdb -O docker docker

# Adjust PostgreSQL configuration so that remote connections to the
# database are possible.
RUN echo "host all  all    0.0.0.0/0  md5" >> /etc/postgresql/9.3/main/pg_hba.conf

# And add ``listen_addresses`` to ``/etc/postgresql/9.3/main/postgresql.conf``
RUN echo "listen_addresses='*'" >> /etc/postgresql/9.3/main/postgresql.conf

WORKDIR /opt/
USER root

# Copying files, setting up folders.
ADD ./ /opt/
RUN mkdir -p /var/lock/apache2 /var/run/apache2 /var/run/sshd /var/log/supervisor
RUN chmod +x /opt/*.sh /opt/*.py

RUN sudo pip3 install -r /opt/requirements.txt
RUN sudo pip install -r /opt/requirements.txt
RUN sudo pip install psycopg2

# download the latest chrome driver binary and place in /usr/bin/
RUN wget http://chromedriver.storage.googleapis.com/2.9/chromedriver_linux64.zip \
	-O /opt/chromedriver_linux64.zip
RUN unzip /opt/chromedriver_linux64.zip
RUN ln -s /opt/chromedriver /usr/bin/chromedriver

# Install Crome Browser
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
RUN sudo sh -c 'echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> \
	/etc/apt/sources.list.d/google.list'
RUN sudo apt-get update && sudo apt-get install -y google-chrome-stable

# Clean up...
RUN ldconfig && \
  apt-get remove -y --purge build-essential libtool && \
  apt-get autoremove -y --purge && \
  apt-get clean -y && \
  rm -rf /tmp/* && \
  rm -rf /var/lib/apt/lists/*

RUN touch /opt/scheduler-log.txt

# Add VOLUMEs to allow backup of config, logs and databases
VOLUME  ["/etc/postgresql", "/var/log/postgresql", "/var/lib/postgresql"]

EXPOSE 22 80 443 5432
CMD ["/usr/bin/supervisord"]
