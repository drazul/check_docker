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

* Output string can be on graphite format adding --enable-performance-data argument.

