# ./jenkins-with-python/Dockerfile
FROM jenkins/jenkins:lts-jdk17

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv && \
    python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    rm -rf /var/lib/apt/lists/*

# alias `python` to `python3`
RUN ln -s /usr/bin/python3 /usr/local/bin/python

# auto-activate the venv for every shell
RUN echo "source /opt/venv/bin/activate" >> /etc/profile.d/activate-venv.sh

# pre-install requirements.txt into Docker image
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install -r /tmp/requirements.txt

USER jenkins
