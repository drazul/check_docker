#!/usr/bin/env python
import argparse
import json
import requests_unixsocket
import sys

nagios_output_state = {
    'OK': 0,
    'WARNING': 1,
    'CRITICAL': 2,
    'UNKNOWN': 3,
}


class Docker(object):

    def __init__(self, args):
        self.docker_socket = args.docker_socket.replace('/', '%2F')
        self.enable_performance_data = args.enable_performance_data

        self.perf_data = list()
        self.summary = list()

        self.check_status = 'OK'

    def __request(self, path):
        session = requests_unixsocket.Session()

        response = session.get('http+unix://%s/%s' % (self.docker_socket, path))
        return response

    def get_all_container_names(self):
        response = self.__request('containers/json')
        names = list()
        for container in response.json():
            names.append(container['Names'][0].replace('/', ''))
        return names

    def get_all_stats_by_name(self):
        stats = list()
        for container in self.get_all_container_names():
            response = self.__request('containers/%s/stats?stream=false' % container)
            stats.append(response.json())
        return stats

    def get_common_stats_by_name(self):
        parsed_stats = dict()
        for stats in self.get_all_stats_by_name():
            parsed_stats[stats['name'].replace('/', '')] = dict(
                cpu_percent=self.__get_cpu_percent(stats),
                memory_percent=self.__get_memory_percent(stats),
                memory_usage_bytes=self.__get_memory_usage(stats),
                net_input_bytes=self.__get_net_io_bytes(stats)[0],
                net_output_bytes=self.__get_net_io_bytes(stats)[1],
                block_input_bytes=self.__get_block_io_bytes(stats)[0],
                block_output_bytes=self.__get_block_io_bytes(stats)[1],
            )
        return parsed_stats

    def __get_cpu_percent(self, stats):
        # via https://github.com/docker/docker/blob/e884a515e96201d4027a6c9c1b4fa884fc2d21a3/api/client/container/stats_helpers.go#L199-L212
        cpu_stats = stats['cpu_stats']
        precpu_stats = stats['precpu_stats']

        cpu_delta = float(cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage'])
        system_delta = float(cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage'])

        percent = 0.0
        if system_delta > 0.0 and cpu_delta > 0.0:
            percent = (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100.0

        return round(percent, 2)

    def __get_memory_usage(self, stats):
        return stats['memory_stats']['usage']

    def __get_memory_percent(self, stats):
        # via https://github.com/docker/docker/blob/e884a515e96201d4027a6c9c1b4fa884fc2d21a3/api/client/container/stats_helpers.go#L109
        percent = (float(stats['memory_stats']['usage']) / float(stats['memory_stats']['limit'])) * 100.0
        return round(percent, 2)

    def __get_net_io_bytes(self, stats):
        # via https://github.com/docker/docker/blob/e884a515e96201d4027a6c9c1b4fa884fc2d21a3/api/client/container/stats_helpers.go#L226-234
        if not 'networks' in stats:
            return 0, 0

        rx = 0
        tx = 0
        for interface, network in stats['networks'].items():
            rx += network['rx_bytes']
            tx += network['tx_bytes']
        return rx, tx

    def __get_block_io_bytes(self, stats):
        # via https://github.com/docker/docker/blob/e884a515e96201d4027a6c9c1b4fa884fc2d21a3/api/client/container/stats_helpers.go#L214-224
        read = 0
        write = 0
        for stat in stats['blkio_stats']['io_service_bytes_recursive']:
            if stat['op'] == 'Read':
                read += stat['value']
            elif stat['op'] == 'Write':
                write += stat['value']
        return read, write

    def __add_performance_data(self, docker_stats):
        for container, stats in docker_stats.items():
            for name, value in stats.items():
                self.perf_data.insert(
                    0,
                    '%s=%s;;;;' % (
                        '%s.%s' % (container, name),
                        value
                    )
                )

    def check_stats(self):
        docker_stats = self.get_common_stats_by_name()

        self.summary.append(json.dumps(docker_stats, indent=4, sort_keys=True))
        self.__add_performance_data(docker_stats)

        self.__set_status()
        self.__nagios_output()

    def __set_status(self):
        self.check_status = 'OK'

    def __nagios_output(self):
        output = self.check_status

        if self.summary:
            output += '\n\n%s' % '\n'.join(self.summary)
        if self.enable_performance_data:
            output += '\n\n|%s' % (' '.join(self.perf_data))

        print(output)
        sys.exit(nagios_output_state[self.check_status])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Return result of a check to docker stats with nagios format')

    parser.add_argument(
        '-s', '--docker-socket',
        help='path to docker socket file',
        type=str,
        default='/var/run/docker.sock',
    )

    parser.add_argument(
        '-a', '--enable-performance-data',
        help='enable output performance data',
        action='store_true',
        default=False
    )

    args = parser.parse_args()

    docker = Docker(args)
    docker.check_stats()
