# ./jenkins-with-python/Dockerfile
FROM jenkins/jenkins:lts-jdk17

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# (optional) make `python` alias to `python3`
RUN ln -s /usr/bin/python3 /usr/local/bin/python

USER jenkins
