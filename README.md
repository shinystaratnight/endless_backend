# Project setup steps

1. Install docker for your operation system (Docker community Edition: CE): https://docs.docker.com/engine/installation/#platform-support-matrix;

2. For using docker without sudo run
    `sudo usermod -aG docker $USER`

3. Run `make .env`. Change `.env` content for your settings (see `env_defaults`);

4. Generate ssh key for git and add generated public key to your bitbucket ssh keys. Set env `PRIVATE_REPO_KEY` to the private key's path value;

5. Keep unique value for `DOCKER_APP_NAME` in  `.env` for all existing instances.


# Nginx configuration

For using system Nginx server set env variable `USE_NGINX_DOCKER` to `0` and `NGINX_CONFIG_PATH` to nginx virtualhost file's directory path.

For using Docker nginx server set env variable `USE_NGINX_DOCKER` to `1` (default).

###  Nginx env variables:

* `DOMAIN_NAME` domain name server (`example.com`)
* `USE_TLS` - switch on/off ssl settings from nginx config file (choices: `0`, `1`. Default: `1`).
    * `0` - disable HTTPS;
    * `1` - enable HTTPS.
* `HTTP_PORT` is a local port for docker routing.
* `HTTPS_PORT` is a local port for docker routing. Would be ignored if `USE_TLS = 0`.

# Docker network settings

### Static ip containers configuration

- `DOCKER_SUB_NET_ROUTE` subnet. During network creation Engine creates a non-overlapping subnetwork for the network by default. This subnetwork is not a subdivision of an existing network. It is purely for ip-addressing purposes. `DOCKER_SUB_NET_ROUTE` will override this default value and specify subnetwork values using the --subnet option.

- `DOCKER_SUB_NET_GATEWAY` network address, IPv4 or IPv6 Gateway for the master subnet.

- `DOCKER_SUB_NET_NAME` local subnet name, would be created if doesn't exists.

- `POSTGRES_CONTAINER_IP` IP-address of the postgres container

- `REDIS_CONTAINER_IP` IP-address of the redis container

- `RABBIT_MQ_CONTAINER_IP` IP-address of the rabbit mq container

- `MEMCACHED_CONTAINER_IP` IP-address of the memcached container

- `NGINX_CONTAINER_IP` IP-address of the nginx container

- `REMOTE_CONTAINER_IP` IP-address of the app container

- `NETWORK_NAME` - subnet name for connecting with clickhouse.

If you want to run multiple `endless_project/forks` instances you should keep env `REMOTE_CONTAINER_IP` as unique value for all instances, also use same `DOCKER_SUB_NET_ROUTE`, `DOCKER_SUB_NET_NAME`.

### Variables
##### Container names:
* `DOCKER_POSTGRES_NAME` - postgres container name (default: `postgres`).
* `DOCKER_MEMCACHED_NAME` - memcached container name (default: `memcached`).
* `DOCKER_REDIS_NAME` - redis container name (default: `redis`).
* `DOCKER_CLICKHOUSE_NAME` - clickhouse container name (default: `clickhouse`).
* `DOCKER_RABBIT_MQ_NAME` - rabbit mq container name (default: `rabbit_mq`).
* `DOCKER_APP_NAME` - app container name, formatted str `ecore-%s` (default: `core` => `ecore-cms`). This name should be unique for the docker running containers.
##### Port binding:
* `DOCKER_NGINX_HTTP_PORT` - docker nginx HTTP port (default: 80). Binding localhost port to docker container (`80` => `nginx-docker`)
* `DOCKER_NGINX_HTTPS_PORT` - docker nginx HTTPS port (default: 443). Binding localhost port to docker container (`443` => `nginx-docker`)
* `DOCKER_POSTGRES_PORT` - docker postgres port (default: `null`). Binding localhost port to docker postgres container (example: `5432` => `postgres-docker`). We can use `PostgreSQL` functionality without installation package in your system.
* `DOCKER_MEMCACHED_PORT` - docker memcached port (default: `null`). See `DOCKER_POSTGRES_PORT`.
* `DOCKER_REDIS_PORT` - docker redis port (default: `null`). See `DOCKER_POSTGRES_PORT`.
* `DOCKER_RABBIT_MQ_PORT` - docker rabbit mq port (default: `null`). See `DOCKER_POSTGRES_PORT`.
#### Extra settings:
* `USE_NGINX_DOCKER` - we can use nginx server without docker (choices: `0`, `1`. Default: `1`):
    * `0`- use nginx from system;
    * `1`- use docker nginx;
* `NGINX_CONFIG_PATH` - if you use system nginx server (`USE_NGINX_DOCKER`=0), set `NGINX_CONFIG_PATH` (default: `/etc/nginx/sites-enabled/`; example: `/usr/local/etc/nginx/servers/`).
* `NGINX_VOLUME` - directory which would be mounted to nginx container and used as `conf` and `www` root. Example: `%s/crm/static, %s/crm/media` & `%s/some-ecore/static`, & `%s/some-ecore/media`, etc. We can use system nginx server, see `USE_NGINX_DOCKER` env.
* `DJANGO_STUFF_URL_PREFIX` -  django stuff prefix. Would be used in urls and nginx configuration.
* `DJANGO_DEBUG` - debug mode (choices: `0`, `1`. Default: `1`).
* `CACHE_KEY_PREFIX` - cache key prefix. Would be used for different projects and the same redis container (default: `ecore-cms`).
* `DJANGO_UWSGI_PORT` - used for `runserver`, `uwsgi` commands. (Default: `8081`).
* `ALLOWED_HOSTS` - Django ALLOWED_HOSTS setting (https://docs.djangoproject.com/en/1.10/ref/settings/#allowed-hosts), use separator `,` (example test.ru,example.com). (Default: `*`)
* `BASE_DIR` -  work directory in the docker container. (Default: `/code`).
* `PRIVATE_REPO_KEY` - SSH key used to get code from private repositories (e.g. endless_core).


# WEB-UI configuration

To use web-ui module set env variable `DJANGO_STUFF_URL_PREFIX`. This variable (`DJANGO_STUFF_URL_PREFIX`) responsible for the django stuff url placement. Web-ui will be available by the root url "/".
For disabling web-ui module set env `DJANGO_STUFF_URL_PREFIX` to the empty value (`DJANGO_STUFF_URL_PREFIX=`).
Example: `DJANGO_STUFF_URL_PREFIX=ecore` (by default) => `/ecore/`, `/ecore/admin`.
This variable used in the Nginx routing configuration.


# CMS

For using cms features there is a default template with simple CMS-page structure. In the marked areas will be placed placeholders and plugins.
There are two placeholder types: `placeholder` and `static_placeholder`.

Notes:

* `static_placeholder`. static_placeholder's content would be available on the all pages with this cms template (example: header, footer).
* `placeholder`. It's content would be available only on one page (example: main content).
* to create page click on `Create page` button.
* to create dynamic pages with dynamic placeholders and reusing them use Snippets. Tt is possible to use django template tags, filters and context (user, request) in the template code.
* page has tree structure, child pages and relative urls (parent: /user/ -> child /user/contacts). You can add child page via toolbar.
* use page permission if page should be available only for logged user (`Page / Permissions` -> check `Login required`).
* to duplicate page with it's content use cms toolbar: (`Page / Create page / Duplicate this page`).


# Make commands
#### Setup docker app
    make

#### Apply migrations
    make migrate

#### Start develop server
    make runserver

#### Collect static
    make static

### Supervisor
#### Supervisord
    make supervisord

#### Supervisor status
    make supervisor

#### Stop/Restart
    make supervisor-stop
    make supervisor-restart
    make restart-uwsgi
    make restart-celery
    make restart-celerycam
    make restart-celery-beat

#### Start all containers
    make docker-start-all

#### Other commands
    make bash-app
    make shell_plus
    make pip-install


# Tests
#### Run tests
    make tests

#### Run tests locally
    pytest

#### Rut tests with coverage
    make tests_cov

#### Rut tests with coverage locally
    pytest --cov=ecore --cov-report=term-missing
