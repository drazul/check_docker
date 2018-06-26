# check_docker
Docker stats on nagios output format

## Summary
* This nagios plugin interact with docker using docker unix socket.
```markdown
Docker unix socket is located, by default, on /var/run/docker.sock
To works fine nagios user needs to be on docker group (usermod -aG docker nagios)
```

* Can be executed from inside a docker container.
It only needs access to unix socket file from docker host.
```markdown
You need add nagios user to deocker group inside docker container.
To do that you can execute (docker group ID can change)
echo "docker:x:993:nagios" >> /etc/group
```

* Output string can be on graphite format adding --enable-performance-data argument.

