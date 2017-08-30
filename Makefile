SHELL := /bin/bash

WEBUI_APP_DIR = webui-app
NGINX_SITE_VOLUME = ""
CURRENT_PATH = $(shell pwd)

PYTHON_3_VERSION = 3.5.2
PYTHON_2_VERSION = 2.7.13
VENV_ROOT = venv
NGINX_DOCKER_VOLUME = /Users/nginx_docker

NGINX_CONF_FILE = var/tmp/nginx.$(DOMAIN_NAME).conf
REDIS_VERSION = alpine
RABBIT_MQ_VERSION = 3

PG_VERSION = 9.6
PG_HBA_PATH = /etc/postgresql/$(PG_VERSION)/main/pg_hba.conf
PG_CONF_PATH = /etc/postgresql/$(PG_VERSION)/main/postgresql.conf
LANG = 'en-au'

include env_defaults
-include .env

PG_LOGIN = -h $(POSTGRES_HOST) -p $(POSTGRES_PORT) -U $(POSTGRES_USERNAME)
PG_LOGIN_POSTGRES = -h $(POSTGRES_HOST) -p $(POSTGRES_PORT) -U postgres

RESTORE_DB_FILE_PATH = var/backups/$(RESTORE_DB_FILE)
RESTORE_DB_FOR_DEV_FILE_PATH = var/backups/$(RESTORE_DB_FOR_DEV_FILE)

define docker_exec
    sudo docker exec $(2) ecore-$(DOCKER_APP_NAME) $(1)
endef

define supervisor
    $(call docker_exec, bin/_supervisorctl $(1))
endef

define nginx_root1
    $(eval NGINX_SITE_VOLUME = $(NGINX_VOLUME)/$(DOCKER_APP_NAME)/)
endef

define nginx_root0
    mkdir -p var/www
    $(eval NGINX_SITE_VOLUME = $(CURRENT_PATH)/var/www/)
endef

define nginx_setup0
    make var/make/local-nginx
endef

define nginx_setup1
    make var/make/docker-nginx
endef

define docker_run
	@if !(sudo docker ps -a -f name=$(2) | grep $(2)); then \
        echo "Run $(1) container"; \
        if test "$(5)"; then \
            echo "Bind localhost port $(4) on $(1)."; \
            sudo docker run -itd -p $(5):$(6) $(3) --name $(2) --net $(DOCKER_SUB_NET_NAME) --ip $(4) $(1); \
        else \
            sudo docker run -itd $(3) --name $(2) --net $(DOCKER_SUB_NET_NAME) --ip $(4) $(1); \
        fi ; \
    fi;
endef

all: \
  var/make \
  var/tmp \
  var/run \
  var/make/subnet \
  var/make/docker-redis \
  var/make-docker-postgres \
  var/make/docker-rabbitmq \
  var/make/create-app \
  var/make/nginx \
  var/make/create-db \
  var/make/docker-clickhouse \
  var/make/connect-to-main-container \
  var/make/webui-app

.env:
	touch .env
	echo "SYSTEM_USER=$(USER)" > .env

var/make:
	mkdir -p var/make

var/run:
	mkdir -p var/run

var/tmp:
	mkdir -p var/tmp

var/www:
	mkdir -p var/www

var/make/node-ppa:
	@if [ ! -f /etc/apt/sources.list.d/nodesource.list ]; then \
		sudo add-apt-repository -y -r ppa:chris-lea/node.js; \
		sudo rm -f /etc/apt/sources.list.d/chris-lea-node_js-*.list; \
		curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key | sudo apt-key add -; \
		echo 'deb https://deb.nodesource.com/node_4.x trusty main\ndeb-src https://deb.nodesource.com/node_4.x trusty main' | sudo tee /etc/apt/sources.list.d/nodesource.list; \
		sudo apt-get update; \
	fi;
	touch $@

var/make/node:
	sudo apt-get install --force-yes -y nodejs
	sudo npm cache clean -f
	sudo npm install -g n
	sudo n lts
	curl -0 -L http://npmjs.org/install.sh | sudo sh
	touch $@

docker-install:
	sudo apt-get install -y --no-install-recommends apt-transport-https ca-certificates curl software-properties-common
	sudo apt-get update
	sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
	sudo apt-get update
	sudo apt-get install -y docker-engine
	sudo apt-add-repository 'deb https://apt.dockerproject.org/repo ubuntu-xenial main'
	sudo usermod -aG docker $(whoami)
	touch $@

var/make/crontab:
	@touch var/tmp/crontab
	@crontab -l > var/tmp/crontab
	$(call docker_exec, bin/app crontab_config >> var/tmp/crontab)
	@cat var/tmp/crontab | crontab
	@rm -f var/tmp/crontab
	@touch $@

rm-subnet:
	if sudo docker network ls | grep "$(DOCKER_SUB_NET_NAME)"; then \
        sudo docker network rm $(DOCKER_SUB_NET_NAME); \
	fi;

var/make/subnet:
	if sudo docker network inspect $(DOCKER_SUB_NET_NAME); then \
	    echo "Subnet already exists"; \
    else \
        if ! sudo docker network create --subnet $(DOCKER_SUB_NET_ROUTE) --gateway $(DOCKER_SUB_NET_GATEWAY) $(DOCKER_SUB_NET_NAME) --opt "com.docker.network.bridge.name"="$(DOCKER_SUB_NET_NAME)"; then \
            exit 1; \
        fi; \
        echo "Subnet successfully created: $(DOCKER_SUB_NET_ROUTE) with name $(DOCKER_SUB_NET_NAME)"; \
    fi;

var/make/create-db:
	make create-postgres-user
	make create-postgres-db
	@touch $@

create-postgres-user:
	sudo docker exec $(DOCKER_POSTGRES_NAME)  bash -c "psql -U postgres -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$(POSTGRES_USER)'\" | \
	     grep -q 1 || createuser -U postgres -d -e -E -l -w -r -s $(POSTGRES_USER)"

create-postgres-db:
	sudo docker exec -it $(DOCKER_POSTGRES_NAME)  bash -c "psql -U postgres -tAc \"SELECT 1 FROM pg_database WHERE datname='$(POSTGRES_DB)'\" | \
	     grep -q 1 || createdb \
	     -E utf8 \
	     -U $(POSTGRES_USER)  \
	     --lc-collate=en_US.UTF-8 \
	     --lc-ctype=en_US.UTF-8 \
	     --encoding=UTF-8 \
	     --template=template0 \
	     $(POSTGRES_DB)"

var/make/nginx:
	$(call nginx_setup$(USE_NGINX_DOCKER))

var/make/local-nginx:
	$(call docker_exec, bin/app nginx_config --site_root=$(CURRENT_PATH)/var/www > $(NGINX_CONF_FILE));
	@if sudo ls $(NGINX_CONFIG_PATH); then \
        sudo rm -f $(NGINX_CONFIG_PATH)/$(DOMAIN_NAME).conf; \
        sudo ln -s $(CURRENT_PATH)/$(NGINX_CONF_FILE) $(NGINX_CONFIG_PATH)/$(DOMAIN_NAME).conf; \
    else \
	    echo "Nginx path not found, you should setup NGINX_CONFIG_PATH env."; \
	    exit 1; \
    fi;
	@touch $@

var/make/docker-nginx:
	make var/make/create-docker-nginx
	make nginx_config/docker
	@touch $@

nginx_config/docker:
	$(call docker_exec, bin/app nginx_config \
	    --site_root=/www/$(DOCKER_APP_NAME) > \
	    $(NGINX_CONF_FILE))
	@sudo cp $(NGINX_CONF_FILE) $(NGINX_VOLUME)/conf/nginx.$(DOMAIN_NAME).conf
	sudo docker restart nginx

var/make/submodules:
	git submodule update --remote
	touch $@

var/make/npm-packages: dependencies/npm.txt
	sudo npm install `cat dependencies/npm.txt`
	find node_modules/ -name "demo" -type d -prune -exec rm -rf "{}" \;
	touch $@

var/make/bower-packages: dependencies/bower.txt
	./node_modules/bower/bin/bower install --allow-root `cat dependencies/bower.txt`
	touch $@

full-clean:
	make clean
	@for CONTAINER in $(DOCKER_POSTGRES_NAME) $(DOCKER_REDIS_NAME) nginx ecore-$(DOCKER_APP_NAME); \
	do \
		if sudo docker ps -a | grep $$CONTAINER; then \
		    echo "Remove container: $$CONTAINER"; \
            sudo docker rm -f $$CONTAINER; \
        fi ; \
	done
	@make clean-clickhouse;
	make rm-subnet

clean:
	@make rm-docker-app;
	@if (sudo docker images | grep ecore-$(DOCKER_APP_NAME)-image); then \
	    sudo docker rmi ecore-$(DOCKER_APP_NAME)-image; \
	    echo "Image removed"; \
	fi ;

	@if (sudo docker ps -a | grep " webui-$(DOCKER_APP_NAME)"); then \
	    sudo docker stop webui-$(DOCKER_APP_NAME); \
	    echo "WEB-UI container stopped"; \
	    sudo docker rm webui-$(DOCKER_APP_NAME); \
	    echo "WEB-UI container removed"; \
	fi ;
	@if (sudo docker images | grep webui-$(DOCKER_APP_NAME)-image); then \
	    sudo docker rmi webui-$(DOCKER_APP_NAME)-image; \
	    echo "WEB-UI image removed"; \
	fi ;
	@rm -rf var/make

drop_db:
	sudo docker stop ecore-$(DOCKER_APP_NAME)
	sudo docker exec $(DOCKER_POSTGRES_NAME) dropdb -U postgres --if-exists $(POSTGRES_DB)

backup_db:
	mkdir -p var/backups/
	touch var/backups/`date +%Y_%m_%d__%H_%M`.bak && \
	ln -sf $(CURRENT_PATH)/var/backups/`date +%Y_%m_%d__%H_%M`.bak var/backups/latest.bak && \
	sudo docker exec -it $(DOCKER_POSTGRES_NAME) pg_dump -U $(POSTGRES_USER) $(POSTGRES_DB) > var/backups/`date +%Y_%m_%d__%H_%M`.bak

backup_db_for_dev:
	mkdir -p var/backups/
	sudo docker exec -it $(DOCKER_POSTGRES_NAME) pg_dump -U $(POSTGRES_USER) $(POSTGRES_DB) > $(RESTORE_DB_FOR_DEV_FILE_PATH)

restore_db:
	make drop_db
	sudo docker cp $(RESTORE_DB_FILE_PATH) $(DOCKER_POSTGRES_NAME):/tmp/$(RESTORE_DB_FILE)
	sudo docker exec -it $(DOCKER_POSTGRES_NAME) pg_restore -U $(POSTGRES_USER) \
		-Fc --create --exit-on-error \
		--dbname postgres \
		--jobs $(RESTORE_DB_JOBS) \
		/tmp/$(RESTORE_DB_FILE)

restore_db_for_dev:
	make drop_db
	make create-postgres-db
	sudo docker cp $(RESTORE_DB_FOR_DEV_FILE_PATH) $(DOCKER_POSTGRES_NAME):/tmp/$(RESTORE_DB_FOR_DEV_FILE)
	sudo docker exec -it $(DOCKER_POSTGRES_NAME) psql -U $(POSTGRES_USER) $(POSTGRES_DB) -f /tmp/$(RESTORE_DB_FOR_DEV_FILE)
	sudo docker exec -it $(DOCKER_POSTGRES_NAME) rm /tmp/$(RESTORE_DB_FOR_DEV_FILE)

clone_prod_db:
	mkdir -p var/backups/
	make prod__backup_db_for_dev
	scp $(PROD_LOGIN):$(PROD_DIR)/var/backups/$(RESTORE_DB_FOR_DEV_FILE) var/backups/
	make restore_db_for_dev

tests:
	PYTHONDONTWRITEBYTECODE=1
	@$(call docker_exec, rm -rf ecore/core/tests/__pycache__/)
	@$(call docker_exec, bash -c "PYTHONDONTWRITEBYTECODE=1 bin/pytest --ds=ecore.settings_tests ecore", -it)

tests_cov:
	@$(call docker_exec, rm -rf ecore/core/tests/__pycache__/)
	@$(call docker_exec, bash -c "PYTHONDONTWRITEBYTECODE=1 bin/pytest --ds=ecore.settings_tests --cov=ecore --cov-report=term-missing ecore", -it)

makemessages:
	$(call docker_exec, bin/django makemessages -l $(LANG) --extension=html,jinja)

compilemessages:
	$(call docker_exec, bin/django compilemessages -l $(LANG))

prod__backup_db:
	ssh $(PROD_LOGIN) "cd $(PROD_DIR) && make backup_db"

prod__backup_db_for_dev:
	ssh $(PROD_LOGIN) "cd $(PROD_DIR) && make backup_db_for_dev"

clean_prod_backups:
	find var/backups/* -type f -mtime +2 -exec rm {} \;
	for i in `find var/backups/*.bak -type f ! -path $$(find var/backups/* -printf '%p\n' | sort -r | head -1)`;  do tar -czvf $$i.tar.gz $$i; rm $$i; done

.PHONY: clean static reload create_db_user create_db drop_db backup_db backup_db_for_dev \
	restore_db restore_db_for_dev clone_prod_db makemessages compilemessages \
	prod__backup_db prod__backup_db_for_dev

check-docker-db:
	@sudo docker ps | grep postgres || echo "Not found";

check-docker-redis:
	@sudo docker ps | grep $(DOCKER_REDIS_NAME) || echo "Not found";

check-docker-app:
	@sudo docker ps | grep crm-core-ecore || echo "Not found";

check-docker-rabbit_mq:
	@sudo docker ps | grep $(DOCKER_RABBIT_MQ_NAME) || echo "Not found";

var/make-docker-postgres:
	@$(call docker_run,postgres:$(PG_VERSION),$(DOCKER_POSTGRES_NAME),,$(POSTGRES_CONTAINER_IP),$(DOCKER_POSTGRES_PORT),5432) \

var/make/docker-redis:
	@$(call docker_run,redis:$(REDIS_VERSION),$(DOCKER_REDIS_NAME),,$(REDIS_CONTAINER_IP),$(DOCKER_REDIS_PORT),6379)

var/make/docker-rabbitmq:
	@$(call docker_run,rabbitmq:$(RABBIT_MQ_VERSION),$(DOCKER_RABBIT_MQ_NAME),,$(RABBIT_MQ_CONTAINER_IP),$(DOCKER_RABBIT_MQ_PORT),5672)

var/make/create-docker-nginx:
	sudo mkdir -p $(NGINX_VOLUME)/conf $(NGINX_VOLUME)/$(DOCKER_APP_NAME)/static/ $(NGINX_VOLUME)/$(DOCKER_APP_NAME)/media/ \
	    $(LETSENCRYPT_CERTS_PATH)
	sudo chmod -R 775 $(NGINX_VOLUME)
	if !(sudo docker ps -a| grep " nginx"); then \
        sudo docker run -itd --name nginx \
            --volume "$(LETSENCRYPT_CERTS_PATH):$(DOCKER_NGINX_CERTS_PATH)" \
            --volume "$(NGINX_VOLUME):/www:ro" \
            --volume "$(NGINX_VOLUME)/conf/:/etc/nginx/conf.d/:ro" \
            --volume "$(CURRENT_PATH)/conf/production/nginx.conf:/etc/nginx/nginx.conf:ro" \
            --net $(DOCKER_SUB_NET_NAME) \
            --ip $(NGINX_CONTAINER_IP) \
            -p $(DOCKER_NGINX_HTTP_PORT):80 \
            -p $(DOCKER_NGINX_HTTPS_PORT):443 \
            nginx; \
	fi;
	@touch $@

rm-docker-nginx:
	if sudo docker ps | grep " nginx"; then \
        sudo docker stop nginx; \
    fi ;
	if sudo docker ps -a | grep " nginx"; then \
        sudo docker rm nginx; \
    fi ;

rm-docker-app:
	@if (sudo docker ps | grep " ecore-$(DOCKER_APP_NAME)"); then \
	    sudo docker stop ecore-$(DOCKER_APP_NAME); \
	fi ;
	@if (sudo docker ps -a | grep " ecore-$(DOCKER_APP_NAME)"); then \
	    sudo docker rm ecore-$(DOCKER_APP_NAME); \
	fi ;
	@rm -f var/make/create-app

var/make/create-app:
	@sudo chmod u+x docker-entrypoint.sh
	@sudo cp $(PRIVATE_REPO_KEY) var/id_rsa
	@if test "$(DJANGO_DEBUG)" = "1"; then \
	    echo "Build docker for dev"; \
        sudo docker build \
             --build-arg "VENV_ROOT=$(VENV_ROOT)" \
             --build-arg "BASE_DIR=$(BASE_DIR)" \
             --build-arg "PRIVATE_REPO_KEY=var/id_rsa" \
             --build-arg "EXPOSE_PORT=$(DJANGO_UWSGI_PORT)" \
             -t ecore-$(DOCKER_APP_NAME)-image \
             -f conf/docker/Dockerfile.dev .; \
	else \
        echo "Build docker for prod"; \
        sudo docker build \
             --build-arg "VENV_ROOT=$(VENV_ROOT)" \
             --build-arg "BASE_DIR=$(BASE_DIR)" \
             --build-arg "PRIVATE_REPO_KEY=var/id_rsa" \
             --build-arg "EXPOSE_PORT=$(DJANGO_UWSGI_PORT)" \
             --build-arg "USER_APP=$(SYSTEM_USER)" \
             -t ecore-$(DOCKER_APP_NAME)-image \
             -f conf/docker/Dockerfile.prod .; \
	fi;
	@sudo rm -f var/id_rsa
	@make run-container
	@touch $@

run-container:
	$(call nginx_root$(USE_NGINX_DOCKER))
	sudo docker run -itd \
        --link "$(DOCKER_POSTGRES_NAME):$(POSTGRES_HOST)" \
        --link "$(DOCKER_REDIS_NAME):$(REDIS_HOST)" \
        --link "$(DOCKER_RABBIT_MQ_NAME):$(RABBIT_MQ_HOST)" \
        --volume "$(CURRENT_PATH)/ecore:$(BASE_DIR)/ecore" \
        --volume "$(CURRENT_PATH)/dependencies/:$(BASE_DIR)/dependencies:ro" \
        --volume "$(CURRENT_PATH)/helpers:$(BASE_DIR)/helpers:ro" \
        --volume "$(CURRENT_PATH)/conf:$(BASE_DIR)/conf" \
        --volume "$(CURRENT_PATH)/docker-entrypoint.sh:$(BASE_DIR)/docker-entrypoint.sh" \
        --volume "$(NGINX_SITE_VOLUME):$(BASE_DIR)/var/www/:rw" \
        --env-file "env_defaults" --env-file ".env" \
        --net $(DOCKER_SUB_NET_NAME) --ip $(REMOTE_CONTAINER_IP) \
        -e WEBUI_APP_DIR=$(WEBUI_APP_DIR) \
        --name ecore-$(DOCKER_APP_NAME) \
        --restart on-failure \
        -p "$(DJANGO_UWSGI_PORT):$(DJANGO_UWSGI_PORT)" \
        ecore-$(DOCKER_APP_NAME)-image

	if test "$(DJANGO_DEBUG)"="1"; then \
		make user_permissions; \
	fi;


restart:
	sudo docker restart ecore-$(DOCKER_APP_NAME)

rebuild:
	git pull
	make clean && make
	sudo docker restart nginx

update:
	git pull
	make migrate
	make static
	make reload

app-logs:
	@sudo docker logs -f --tail 10 ecore-$(DOCKER_APP_NAME)

nginx-logs:
	@sudo docker logs -f --tail 20 nginx

runserver:
	@$(call docker_exec, bin/django runserver 0.0.0.0:$(DJANGO_UWSGI_PORT), -it)

pip-install:
	@$(call docker_exec, bin/pip install -r dependencies/pip_py3.txt)

static:
	@$(call docker_exec, bin/django collectstatic --noinput)

migrate:
	@$(call docker_exec, bin/django migrate, -it)

makemigrations:
	@$(call docker_exec, bin/django makemigrations, -it)

reload:
	@$(call docker_exec, touch var/run/uwsgi_reload)

bash-app:
	@$(call docker_exec, bash, -it)

bash-db:
	@docker exec -it $(DOCKER_POSTGRES_NAME) bash

shell_plus:
	@$(call docker_exec, bin/django shell_plus, -it)

supervisord:
	@$(call docker_exec, bin/_supervisord)

supervisor:
	@$(call supervisor, status all)

supervisor-stop:
	@$(call supervisor, stop all)

supervisor-restart:
	@$(call supervisor, restart all)

restart-uwsgi:
	@$(call supervisor, restart uwsgi)

restart-celery:
	@$(call supervisor, restart celery-worker)

restart-celerycam:
	@$(call supervisor, restart celerycam)

restart-celery-beat:
	@$(call supervisor, restart celery-beat)

create-superuser:
	@$(call docker_exec, bin/django createsuper, -it)

docker-app-ip:
	@echo "Container IP: $$(sudo docker inspect --format "{{ .NetworkSettings.IPAddress }}" ecore-$(DOCKER_APP_NAME))"

docker-start-all:
	sudo docker start $(DOCKER_POSTGRES_NAME) $(DOCKER_REDIS_NAME) $(DOCKER_RABBIT_MQ_NAME) ecore-$(DOCKER_APP_NAME)

var/make/webui-app:
	@if test "$(DJANGO_STUFF_URL_PREFIX)"; then \
		echo "WEB-UI installation..."; \
		if ! ls $(WEBUI_APP_DIR); then \
			git clone git@bitbucket.org:r3sourcer_1/endless_webui.git $(WEBUI_APP_DIR); \
		else \
			git pull; \
		fi; \
		$(call nginx_root$(USE_NGINX_DOCKER)) \
		mkdir -p $(NGINX_VOLUME)/$(DOCKER_APP_NAME)/webui/; \
		mkdir -p var/www/webui; \
		sudo chmod -R 775 $(NGINX_VOLUME)/$(DOCKER_APP_NAME)/webui/; \
		sudo chmod u+x $(WEBUI_APP_DIR)/docker-entrypoint.sh; \
		docker build --tag webui-$(DOCKER_APP_NAME)-image $(WEBUI_APP_DIR); \
		docker run -itd \
            --name webui-$(DOCKER_APP_NAME) \
            -v $(NGINX_SITE_VOLUME)$(WEBUI_APP_DIR):/www/ \
            -v $(shell pwd)/$(WEBUI_APP_DIR)/:/code/ \
            --env-file "env_defaults" --env-file ".env" \
            webui-$(DOCKER_APP_NAME)-image; \
        echo "WEB-UI successfully installed."; \
    else \
        echo "The 'WEB-UI' wasn't installed because ENV 'DJANGO_STUFF_URL_PREFIX' disabled"; \
	fi;
	@touch $@

var/make/docker-clickhouse:
	if !(sudo docker ps -a| grep " $(DOCKER_CLICKHOUSE_NAME)"); then \
		sudo chmod u+x clickhouse-entrypoint.sh; \
		sudo python helpers/clickhouse_config.py; \
		sudo docker run \
			--volume "$(CURRENT_PATH)/clickhouse-entrypoint.sh:/var/lib/clickhouse/clickhouse-entrypoint.sh" \
			--entrypoint /var/lib/clickhouse/clickhouse-entrypoint.sh \
		 	-d --name $(DOCKER_CLICKHOUSE_NAME) --ulimit nofile=262144:262144 yandex/clickhouse-server; \
		sudo docker cp users.xml $(DOCKER_CLICKHOUSE_NAME):/etc/clickhouse-server/ ; \
	fi ;

var/make/connect-to-main-container:
	if !(sudo docker network ls| grep " $(NETWORK_NAME)"); then \
		sudo docker network create -d bridge --subnet 172.25.0.0/16 $(NETWORK_NAME); \
	fi ;
	if !(sudo docker network inspect $(NETWORK_NAME)| grep "$(DOCKER_CLICKHOUSE_NAME)"); then \
		sudo docker network connect $(NETWORK_NAME) $(DOCKER_CLICKHOUSE_NAME); \
	fi ;
	if !(sudo docker network inspect $(NETWORK_NAME)| grep "ecore-$(DOCKER_APP_NAME)"); then \
		sudo docker network connect $(NETWORK_NAME) ecore-$(DOCKER_APP_NAME); \
	fi ;

clean-clickhouse:
	if (sudo docker network inspect $(NETWORK_NAME)| grep "$(DOCKER_CLICKHOUSE_NAME)"); then \
		sudo docker network disconnect $(NETWORK_NAME) $(DOCKER_CLICKHOUSE_NAME); \
	fi ;
	if (sudo docker network inspect $(NETWORK_NAME)| grep "ecore-$(DOCKER_APP_NAME)"); then \
		sudo docker network disconnect $(NETWORK_NAME) ecore-$(DOCKER_APP_NAME); \
	fi ;
	if (sudo docker network ls| grep " $(NETWORK_NAME)"); then \
		sudo docker network rm $(NETWORK_NAME); \
	fi ;
	if (sudo docker ps| grep " $(DOCKER_CLICKHOUSE_NAME)"); then \
		sudo docker stop $(DOCKER_CLICKHOUSE_NAME); \
	fi ;
	if (sudo docker ps -a| grep " $(DOCKER_CLICKHOUSE_NAME)"); then \
		sudo docker rm $(DOCKER_CLICKHOUSE_NAME); \
	fi ;

user_permissions:
	sudo docker exec -it -u 0 ecore-$(DOCKER_APP_NAME) chown $(SYSTEM_USER):$(SYSTEM_USER) var/www/ -R;
