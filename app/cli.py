#!/usr/bin/env python
#  -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os
import sys
import traceback
from itertools import chain

import click
import requests 


def iflatmap(f, items):
    return chain.from_iterable(map(f, items))


def _get_eureka_url():
    eureka_host = os.environ.get('EUREKA_HOST')

    if not eureka_host:
        raise Exception("You must define EUREKA_HOST environment variable")
    
    if "apps" in eureka_host:
        return eureka_host

    return "http://{}/eureka-server/v2/apps".format(eureka_host)


def _request_eureka_inventory():
    url = _get_eureka_url()

    response = requests.get(url, headers={"Accept": "application/json"})

    return response.json()["applications"]["application"]


def _is_hostname(hostname):
    def __in(hosts):
        return hostname == hosts.get("hostName")

    return __in


def _build_ansible_host(instances):
    return {
        "hosts": map(lambda instance: instance["hostName"], instances),
    }


def _build_ansible_inventory_groups(eureka_response):
    return dict(map(lambda item: (item["name"], _build_ansible_host(item["instance"])), eureka_response))


def _build_ansible_metadata(eureka_response):
    eureka_instances = _get_eureka_client_instances(eureka_response)
    host_by_metadata = _get_eureka_client_metadata_by_host(eureka_instances)

    return {
        "_meta": {
            "hostvars": host_by_metadata
        }
    }


def _get_eureka_client_metadata_by_host(eureka_instances):
    return dict(map(lambda item: (item["hostName"], item), eureka_instances))


def _get_eureka_client_instances(eureka_reponse):
    return list(iflatmap(lambda item: item["instance"], eureka_reponse))


def _list_cli():
    eureka_response = _request_eureka_inventory()

    inventory_list = _build_ansible_inventory_groups(eureka_response)
    metadata = _build_ansible_metadata(eureka_response)

    ansible_inventory = dict(inventory_list.items() + metadata.items())

    print(json.dumps(ansible_inventory, indent=2))


def _host_cli(hostname):
    hosts = iflatmap(lambda item: item.get("instance", {}), _request_eureka_inventory())

    host_info = next(filter(_is_hostname(hostname), hosts), {})

    print(json.dumps(host_info, indent=2))


@click.command()
@click.pass_context
@click.option('--list', '-l', is_flag=True, help="Lists the hosts.")
@click.option('--host', '-h', help="Show information of a given host.")
def run_cli(ctx, list, host):
    try:
        if list:
            _list_cli()
        elif host:
            _host_cli(host)
        else:
            print(ctx.get_help())

    except Exception as ex:
        traceback.print_exc(file=sys.stderr)
        print("Trying to request at {}".format(_get_eureka_url()), file=sys.stderr)
        exit(-1)


if __name__ == '__main__':
    run_cli()

