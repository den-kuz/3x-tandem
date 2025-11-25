FROM alpine:3.20

RUN apk add --no-cache openssh-client ansible git rsync sshpass py3-pip && \
    pip install six netaddr passlib paramiko --break-system-packages && \
    mkdir -p /root/.ssh && \
    echo "Host *" > /root/.ssh/config && echo " StrictHostKeyChecking no" >> /root/.ssh/config

RUN apk add --update --no-cache ansible bash openssh sshpass
RUN ansible-galaxy collection install community.docker --force

COPY ./ansible /ansible
COPY ./scripts /scripts
COPY ./data /data

WORKDIR /ansible

CMD ["ansible", "--help"]
