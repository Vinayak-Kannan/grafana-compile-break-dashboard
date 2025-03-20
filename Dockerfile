FROM python:3.12-bookworm
USER root

RUN apt update \
 && apt install -y fontconfig openjdk-17-jre

RUN wget -O /usr/share/keyrings/jenkins-keyring.asc \
  https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
 && echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc]" \
  https://pkg.jenkins.io/debian-stable binary/ | tee \
  /etc/apt/sources.list.d/jenkins.list > /dev/null \
 && apt-get update \
 && apt-get install -y jenkins

#change back to user jenkins
USER  jenkins

# Start Jenkins
ENTRYPOINT ["/usr/bin/jenkins"]
