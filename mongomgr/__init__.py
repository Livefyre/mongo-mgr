#!/usr/bin/env python
# Buckets timestamps by some data property.

import pdb
import sys
from time import sleep
from pprint import pformat, pprint
import os
from pyyacc.parser import build
from pymongo import MongoReplicaSetClient
from pymongo import MongoClient
from pymongo import DESCENDING as dec
from pymongo import ASCENDING as asc
from pymongo.errors import AutoReconnect
from docopt import docopt
from functools import partial
from operator import ge, le

CONNECTION_ARGS = { "socketTimeoutMS":1000,
                    "connectTimeoutMS":1000}
def verb_list(args, config):
  print "\n".join(config['ConnectionStrings'].keys())
  exit(0)

def verb_config(args, config):
    mc = get_mc(args, config)
    repl_config = get_config(mc)
    pprint(repl_config)
    exit(0)

def verb_status(args, config):
    mc = get_mc(args, config)
    status = get_status(mc)
    pprint(status)
    exit(0)

def verb_add(args, config):
    hostname = args['<hostname>']
    mc = get_mc(args, config)
    repl_config = get_config(mc)

    max_id = 0
    for host in repl_config['members']:
        assert(host['host'] != hostname)
        max_id = max(max_id, host['_id'])

    host_config = {'_id': max_id + 1, 'host': hostname, 'hidden': True, 'priority': 0}

    repl_config['members'].append(host_config)
    repl_config['version'] += 1

    result = mc.admin.command("replSetReconfig", repl_config)
    print "Result of query was", result
    exit(0)

def verb_remove(args, config):
    hostname = args['<hostname>']
    mc = get_mc(args, config)
    repl_config = get_config(mc)

    primary = get_primary(mc)
    if hostname == primary:
        print "You are trying to remove the primary!"
        exit(1)

    hosts = map(lambda x: x['host'], repl_config['members'])
    try:
        rm_idx = hosts.index(hostname)
        repl_config['members'].pop(rm_idx)
        repl_config['version'] += 1
        result = mc.admin.command("replSetReconfig", repl_config)
        print "Result of the query was %s" % result
        exit(0)
    except ValueError:
        print "Host name not in repl members"
        exit(0)

def verb_demote(args, config):
    hostname = args['<hostname>']
    mc = get_mc(args, config)
    repl_config = get_config(mc)

    primary = get_primary(mc)
    if primary == hostname:
        print primary, "Stepping down"
        result = mc.admin.command('replSetStepDown', 60)
        print result
        exit(0)
    else:
        print "Current primary is", primary, "cannot demote", hostname
        exit(1)

def verb_hide(args, config):
    hostname = args['<hostname>']
    mc = get_mc(args, config)
    primary = get_primary(mc)
    if primary == hostname:
        print "Cannot hide the primary:", primary
        exit(1)

    repl_config = get_config(mc)
    for member in repl_config['members']:
        if member['host'] == hostname:
            break
    else:
        print hostname, "is not a member of the replset."
        exit(1)

    if member.get('priority') == 0 and member.get('hidden'):
        print hostname, "is already hidden."
        exit(0)

    member['priority'] = 0
    member['hidden'] = True
    repl_config['version'] += 1
    reconfig(repl_config, mc)
    exit(0)

def verb_unhide(args, config):
    hostname = args['<hostname>']
    mc = get_mc(args, config)
    primary = get_primary(mc)
    repl_config = get_config(mc)
    for member in repl_config['members']:
        if member['host'] == hostname:
            break
    else:
        print hostname, "is not a member of the replset."
        exit(1)

    if member.get('priority') != 0 and member.get('hidden') != True:
        print hostname, "is not hidden."
        exit(0)

    member.pop('priority', None)
    member['hidden'] = False
    repl_config['version'] += 1
    reconfig(repl_config, mc)
    exit(0)

def check_wrapper(check, args, config):
    def check_logic(args, config, result, output):
        crit = int(args['<critical>'])
        warn = int(args['<warn>'])

        if crit >= warn:
          cmp = ge
        elif crit < warn:
          cmp = le

        if cmp(result, crit):
            print 'CRITICAL:', output
            exit(2)
        elif cmp(result,warn):
            print 'WARN:', output
            exit(1)
        else:
            print 'SUCCESS:', output
            exit(0)
    try:
        results = check(args, config)
    except Exception as e:
        print "UNKNOWN:", type(e), e
        exit(3)
    else:
      check_logic(args, config, *results)

def check_members(args, config):
  mc = get_mc(args, config)
  status = get_status(mc)
  members = status['members']
  unhealthy_members = filter(lambda member: member['stateStr'] not in ('PRIMARY','SECONDARY'), members)
  unhealthy_strs = ["%s %s" % (member['name'], member['stateStr']) for member in unhealthy_members]
  return len(unhealthy_strs), "%s hosts are unhealthy\n" % len(unhealthy_strs) + "\n".join(unhealthy_strs)

def check_lag(args, config):
    mc = get_mc(args, config)
    repl_status = get_status(mc)
    repl_config = get_config(mc)

    members_status = repl_status['members']
    members_config = repl_config['members']

    visible = [ member['host'] for member in members_config if not member.get('hidden')]
    primary = filter(lambda member_status: member_status['stateStr'] in ('PRIMARY'), members_status)[0]
    lag_times = {member_status['name']:(primary['optimeDate'] - member_status['optimeDate']).total_seconds() for member_status in members_status if member_status['name'] in visible}


    max_lag = max(lag_times.values())
    host_strings = ["%s: %s seconds" % h for h in lag_times.items()]
    lag_str = 'max lag is ' + str(max_lag) + ' sec\n' + "\n".join(host_strings)
    return (max_lag, lag_str)

def get_db_sizes(hostname):
    with MongoClient(hostname, **CONNECTION_ARGS) as m:
        dbs = m.admin.command('listDatabases')['databases']
    return dbs

def check_size(args, config):
    mc = get_mc(args, config)
    members = get_config(mc)['members']
    (primary_host, primary_port) = mc.primary

    with MongoClient(primary_host, primary_port, **CONNECTION_ARGS) as m:
        dbs = m.admin.command('listDatabases')['databases']
        pri_sizes = {db['name']:m[db['name']].command('dbStats')['dataSize'] for db in dbs}

    secondaries = filter(lambda member: member['host'] != primary_host, members)
    sec_db_size = {member['host']:{db['name']:m[db['name']].command('dbStats')['dataSize'] for db in get_db_sizes(member['host']) } for member in secondaries}
    sec_size_deltas = []
    for host,dbs in sec_db_size.items():
      for name, sec_size in dbs.items():
        try:
          sec_size_deltas.append( (host, name, int((abs(pri_sizes[name] - sec_size)/pri_sizes[name]))*100) )
        except ZeroDivisionError:
          if sec_size == 0:
            sec_size_deltas.append( (host, name, 0) )
          else:
            sec_size_deltas.append( (host, name, float('inf')) )
        except KeyError as e:
          print "Missing db:", e.args
    max_delta = max([delta for _,_,delta in sec_size_deltas])
    sec_size_deltas = filter(lambda x: x[2] > 0.0, sec_size_deltas)
    delta_strs = ["%s %s %s" % (host, db, delta) for host, db, delta in sec_size_deltas]
    return max_delta, "MAX delta is %s" % max_delta + "\n".join(delta_strs)

def check_oplog(args, config):
    mc = get_mc(args, config)
    members = get_config(mc)['members']
    hosts = [member['host'] for member in members]

    status = get_status(mc)
    primary = filter(lambda member: member['stateStr'] in ('PRIMARY'), status['members'])[0]
    primary_time = primary['optime']

    oplog_starts = {host: get_oplog_start(host) for host in hosts}
    oplog_deltas = {host: primary_time.time - ts.time for (host, ts) in oplog_starts.items()}
    min_delta = min([delta for _,delta in oplog_deltas.items()])

    delta_strs = ["%s %s" % (host, delta) for host, delta in oplog_deltas.items()]
    return min_delta, "MIN delta is %s\n" % min_delta + "\n".join(delta_strs)

def get_mc(args, config):
    replica_set  = args["<replica-set>"]
    conn_strings = config['ConnectionStrings'][replica_set]
    mc = MongoReplicaSetClient(",".join(conn_strings), replicaSet=replica_set, **CONNECTION_ARGS)
    return mc

def get_config(mc):
    local = mc.local
    config = local.system.replset.find_one()
    return config

def get_status(mc):
    status = mc.admin.command('replSetGetStatus', 1)
    return status

def get_oplog_start(hostname):
    with MongoClient(hostname, **CONNECTION_ARGS) as m:
        dbs = m.admin.command('listDatabases')['databases']
        local = m.local
        oplog = local.oplog.rs
        timestamp = oplog.find().sort('$natural', asc).limit(1)[0]['ts']
    return timestamp

def reconfig(cfg, mc):
    # A reconfig always causes a reconnect. This is ok.
    try:
        mc.admin.command("replSetReconfig", cfg)
    except AutoReconnect:
        pass
    new_cfg = get_config(mc)
    assert new_cfg == cfg, (new_cfg, cfg)
    return new_cfg

def get_primary(mc):
    tries = 5
    while tries > 0:
        try:
            primary = '%s:%s' % mc.primary
            break
        except:
            tries -= 1
            sleep(1)
    if not tries:
        print 'Could not get primary info in a timely manner, exiting'
        sys.exit(1)
    return primary

usage = \
"""
mongo_mgr. A MongoDB management tool.

Usage:
  mongomgr [options] list
  mongomgr [options] <replica-set> (config|status)
  mongomgr [options] <replica-set> (add|remove|demote|hide|unhide) <hostname>
  mongomgr [options] <replica-set> check-lag <warn> <critical>
  mongomgr [options] <replica-set> check-size <warn> <critical>
  mongomgr [options] <replica-set> check-members <warn> <critical>
  mongomgr [options] <replica-set> check-oplog <warn> <critical>

Options:
  -h --help        Show this screen.
  --version        Show version.
  --config=<conf>  Comma separated config files.
"""

verb_map = {
 'list': verb_list,
 'config': verb_config,
 'status': verb_status,
 'add': verb_add,
 'remove': verb_remove,
 'demote': verb_demote,
 'hide': verb_hide,
 'unhide': verb_unhide,
 'check-lag': partial(check_wrapper, check_lag),
 'check-size': partial(check_wrapper, check_size),
 'check-members': partial(check_wrapper, check_members),
 'check-oplog': partial(check_wrapper, check_oplog),
}

_ROOT = os.path.abspath(os.path.dirname(__file__))

def main():
    args = docopt(usage)
    app_yaml = os.path.join(_ROOT, "app.yaml")
    if args['--config'] is not None:
      config_paths = args['--config'].split(",")
    else:
      config_paths = list()
    config_files = [app_yaml] + config_paths
    builder, settings_dict = build(*config_files)
    verbs = [function for (name, function) in verb_map.items() if args[name]]
    assert len(verbs) == 1
    verbs[0](args, settings_dict['MongoConnections'])

if __name__ == "__main__":
    main()
