# 0081: How Keel scales an application past one machine (the problems Kubernetes solves)

Date: 2026-11-07
Status: **proposed, not decided**. The maintainer asked for this note on
2026-11-07, for later work. Nothing in it is built yet.

## The question

A Keel application runs in one container (LXC) or VM, and that container
can be large (16 GB, 32 GB of RAM). When the application reaches the limit
of its bare-metal host, how does Keel grow it onto more machines, as
Kubernetes does with many pods?

## What Kubernetes really does

1. Kubernetes scales only the **stateless** part of an application: the
   code that answers requests (PHP of WordPress, Odoo workers, Laravel
   web). The "100 pods" are 100 copies of that code behind a load balancer
   (a Service or an Ingress).
2. A copy can be added or removed at any time only because no copy keeps
   state. The state lives **outside** the pods:
   - the database: a managed service, or an operator (for example
     CloudNativePG, Galera);
   - the uploaded files: object storage (S3);
   - sessions and cache: Redis.
3. Kubernetes does not shard a database. A database still has one primary
   for writes and read replicas. Sharding is a decision of the application,
   and most applications never need it.
4. Helm only makes YAML from templates. It does not scale anything.
5. The Horizontal Pod Autoscaler adds or removes copies from a metric
   (CPU, requests).

So Kubernetes solves "run N copies and spread the requests". It moves the
hard problem, the state, to other services.

## Keel today

The Keel pair (decisions 0050, 0054, 0057) is **high availability, not
scale**. The replica only reads and takes over when the primary fails. All
the load of the application is on one machine.

## Proposed model, in steps

Each step is useful by itself. Do them in this order, and only when the
load needs it.

1. **Database apart from the application.** The database in its own
   container, the application in another. This alone moves the limit up.
2. **Application node role.** A new role: the same application image,
   with no local database and no local state.
   - It connects to the database through the VIP of the database pair.
   - It joins the cluster with an invite, like the `keel2:` invite of
     cloud mode.
   - It can be added or removed at any time.
3. **Load balancer.** The nginx of keel-web spreads the requests across
   the application nodes, with health checks. The VIP moves to the load
   balancer pair.
4. **Shared state.**
   - Files: Syncthing (decision 0050) is good for 2 or 3 nodes. For more
     nodes, use object storage that we host: Garage or MinIO, in their own
     containers. WordPress uploads and the Odoo filestore go there.
   - Sessions and cache: Redis behind a VIP (decision 0068 pair model).
5. **Read replicas** for the parts that read the most (Odoo reports,
   WordPress pages). The application must send those reads to a replica.
6. **Sharding** only as the last step, and per application.

## Per application

- **WordPress:** scales well. N PHP nodes, a page cache, uploads in
  object storage.
- **Laravel:** N web nodes and N queue-worker nodes, with Redis for
  cache, sessions and queues.
- **Odoo:** N worker nodes. The longpolling (websocket) needs sticky
  sessions on the load balancer. The filestore must be shared.

## The constraint of our networks

Decision premise: sites can be about 250 ms RTT apart, with jitter and
loss. An application node far from the database primary waits that RTT
on each query. So:

- **scale** (many application nodes) stays **inside one site**, near the
  primary;
- the link **between sites** stays **high availability**, as today.

## Automatic scaling

The equivalent of the Horizontal Pod Autoscaler is a service that uses the
Proxmox API:

1. it reads a metric (CPU, requests, queue length);
2. it clones the application template;
3. the new node joins with an invite;
4. the load balancer adds it, or removes a node when the load goes down.

This is part of the multi-host "cloud system" that the maintainer wants
later, as a separate project.

## Open questions for the maintainer

1. Object storage: Garage (small, made for poor networks, AGPL) or MinIO?
2. Is the application node a new mode in the install screen (next to
   standalone, cloud, cloud advanced), or a role that `keel` adds later?
3. Which application is first? WordPress is the simplest.
