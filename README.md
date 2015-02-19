# mongo-mgr
Utility for managing mongo replica sets.

```
Usage:
  mongomgr [options] list
  mongomgr [options] <replica-set> (config|status)
  mongomgr [options] <replica-set> (add|remove|demote|hide|unhide) <hostname>
  mongomgr [options] <replica-set> check-lag <warn> <critical>
  mongomgr [options] <replica-set> check-size <warn> <critical>
  mongomgr [options] <replica-set> check-members <warn> <critical>
  mongomgr [options] <replica-set> check-oplog <warn> <critical>
  ```
  
# Configuration Verbs:

## List:
Lists possible replica sets to connect to.
```
vagrant@puppet.localdev.livefyre.com:~$ mongomgr list
lfdjrepl
lfsprepl
```

## Status:
Show replica set status.
```
vagrant@puppet.localdev.livefyre.com:~$ mongomgr lfdjrepl status
{u'date': datetime.datetime(2015, 2, 19, 3, 33, 10),
 u'members': [{u'_id': 12,
               u'health': 1.0,
               u'lastHeartbeat': datetime.datetime(2015, 2, 19, 3, 33, 9),
               u'lastHeartbeatRecv': datetime.datetime(2015, 2, 19, 3, 33, 9),
               u'name': u'mg-lfdjrepl14.qa.livefyre.com:27017',
               u'optime': Timestamp(1424316789, 350),
               u'optimeDate': datetime.datetime(2015, 2, 19, 3, 33, 9),
               u'pingMs': 0,
               u'state': 2,
               u'stateStr': u'SECONDARY',
               u'syncingTo': u'mg-lfdjrepl17.qa.livefyre.com:27017',
               u'uptime': 1221943},
              {u'_id': 13,
               u'health': 1.0,
               u'lastHeartbeat': datetime.datetime(2015, 2, 19, 3, 33, 9),
               u'lastHeartbeatRecv': datetime.datetime(2015, 2, 19, 3, 33, 9),
               u'name': u'mg-lfdjrepl13.qa.livefyre.com:27017',
               u'optime': Timestamp(1424315838, 453),
               u'optimeDate': datetime.datetime(2015, 2, 19, 3, 17, 18),
               u'pingMs': 0,
               u'state': 3,
               u'stateStr': u'RECOVERING',
               u'syncingTo': u'mg-lfdjrepl14.qa.livefyre.com:27017',
               u'uptime': 6994},
              {u'_id': 14,
               u'health': 1.0,
               u'name': u'mg-lfdjrepl17.qa.livefyre.com:27017',
               u'optime': Timestamp(1424316790, 72),
               u'optimeDate': datetime.datetime(2015, 2, 19, 3, 33, 10),
               u'self': True,
               u'state': 1,
               u'stateStr': u'PRIMARY',
               u'uptime': 1313625}],
 u'myState': 1,
 u'ok': 1.0,
 u'set': u'lfdjrepl'}
 ```
## Config
Shows replica set config document.
```
vagrant@puppet.localdev.livefyre.com:~$ mongomgr lfdjrepl config
{u'_id': u'lfdjrepl',
 u'members': [{u'_id': 12, u'host': u'mg-lfdjrepl14.qa.livefyre.com:27017'},
              {u'_id': 13,
               u'hidden': True,
               u'host': u'mg-lfdjrepl13.qa.livefyre.com:27017',
               u'priority': 0.0},
              {u'_id': 14, u'host': u'mg-lfdjrepl17.qa.livefyre.com:27017'}],
 u'version': 185614}
 ```
 
# Management Verbs
## add
Add testhost to the replica set.
```
vagrant@puppet.localdev.livefyre.com:~$ mongomgr lfdjrepl add testhost:27017
Result of query was {u'down': [u'testhost:27017'], u'ok': 1.0}
```
## remove
Remove testhost to replica set.
```
vagrant@puppet.localdev.livefyre.com:~$ mongomgr lfdjrepl remove testhost:27017
```

## demote
Demote a host so that its not the primary.
```
vagrant@puppet.localdev.livefyre.com:~$ mongomgr lfdjrepl demote mg-lfdjrepl17.qa.livefyre.com:27017
```
## hide
Hide a host so it doesn't recieve secondary reads.
```
mongomgr lfdjrepl hide mg-lfdjrepl17.qa.livefyre.com:27017
```
## unhide
Make a host elidgible for secondary reads.
```
mongomgr lfdjrepl unhide mg-lfdjrepl14.qa.livefyre.com:27017
```
# Check Verbs
mongomgr check verbs obey the nagios return code convention and make great nagios checks.

## check-lag
Check to see how far behind replication is on secondaries.
Warn if less than 10 seconds behind, critical if more than 20 seconds behind.
```
mongomgr lfdjrepl check-lag 10 20
CRITICAL: max lag is 2224.0 sec
mg-lfdjrepl13.qa.livefyre.com:27017: 2224.0 seconds
mg-lfdjrepl17.qa.livefyre.com:27017: 0.0 seconds
```

## check-members
Check if members of the replica set are healthy. Because mongo is quarum based, the number of hosts in non-ok states is configurable.
```
vagrant@puppet.localdev.livefyre.com:~$ mongomgr lfdjrepl check-members 1 2
WARN: 1 hosts are unhealthy
mg-lfdjrepl13.qa.livefyre.com:27017 RECOVERING
```

## check-oplog
Make sure that the oplog start is at least n seconds in the past.
```
vagrant@puppet.localdev.livefyre.com:~$ mongomgr lfdjrepl check-oplog  $((48*3600)) $((24*3600))
SUCCESS: MIN delta is 486076
mg-lfdjrepl13.qa.livefyre.com:27017 492842
mg-lfdjrepl17.qa.livefyre.com:27017 486076
mg-lfdjrepl14.qa.livefyre.com:27017 486095
```

## check-size
Make sure that the database sizes on the secondaries match the master. This is meant to spot rare replication errors whcih can sometimes drop data.
Crit and warn parameters are percents ( 0 - 100).
```
vagrant@puppet.localdev.livefyre.com:~$ mongomgr lfdjrepl check-size 10 20
SUCCESS: MAX delta is 0
```
