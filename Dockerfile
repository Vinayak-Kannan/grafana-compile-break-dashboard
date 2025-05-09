# ./Dockerfile
FROM jenkins/jenkins:lts-jdk17

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv && \
    python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    chown -R jenkins:jenkins /opt/venv && \
    rm -rf /var/lib/apt/lists/*

# alias `python` to `python3`
RUN ln -s /usr/bin/python3 /usr/local/bin/python

# pre-install requirements.txt into Docker image
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install -r /tmp/requirements.txt

USER jenkins
