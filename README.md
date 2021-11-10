# Resource Hub API

Resource Hub API/backend service

Usage:

```bash
# creates new configuration files for customization...
cp -n .env.defaults .env
cp -n config/keycloak-config.json.defaults config/keycloak-config.json
cp -n data/vault.example.yml data/vault.yml

# Build and start containers
docker-compose build --progress=plain # creates rhub-api docker image
docker-compose up  # starts the api
```

Additionally, for convenience, there is a `Makefile` with some useful commands:

```bash
$ make init           # create new customized .env and vault.yml files
$ make build          # build docker image
$ make build-no-cache # build docker image, ignoring the cache
$ make start          # start the orchestration using docker-compose
$ make stop           # stop orchestration
$ make test           # run unit tests (needs PYTHONPATH or virtualenv set)
```

## Requirements

The API requires other services (keycloak, database, etc) in order to function.
Some of the configuration comes from environment variables. Docker-compose in
this repository is configured to read variables from the customized `.env` file.

### Keycloak

You may wish to start by creating a separate "realm" in Keycloak for the
Resource Hub. If so, also create an admin account which can be used by the API
to make authenticated requests to keycloak. Then within the realm create a new
client for the API with the following configuration:

* "Access Type" of the client must be set to "confidential", otherwise it is not
  possible to make changes in realm (manage users, groups and roles)
* "Service Accounts Enabled" set to "on" and under tab "Service Account Roles"
  select "realm-management" in "Client Roles" dropdown and assign "manage-user"
  and "manage-realm" roles.
* "Standard Flow Enabled" set to "off" because this client is not used to
  authenticate end-users but only from API.
* Other parameters may remain at the default values.

Once you have configured the Keycloak, go to your client configuration, open the
"Installation" tab and select "Keycloak OIDC JSON". Generated file contains
parameters that are required by the API/backed, copy-paste them to appropriate
variables in `.env` file (see below).

* `KEYCLOAK_ADMIN_PASS` - .admin password
* `KEYCLOAK_ADMIN_USER` - .admin username or any user that can manage users,
  groups an roles in Keycloak (has "manage-user" and "manage-realm" roles)
* `KEYCLOAK_REALM` - .realm from OIDC JSON
* `KEYCLOAK_RESOURCE` - .resource from OIDC JSON
* `KEYCLOAK_SECRET` - .credentials.secret from OIDC JSON
* `KEYCLOAK_SERVER` - .auth-server-url from OIDC JSON

### PostgreSQL

In the PostgreSQL you just need to create database and user, tables and other
object are created automatically on first start.

* `RHUB_DB_DATABASE`
* `RHUB_DB_HOST`
* `RHUB_DB_PASSWORD`
* `RHUB_DB_PORT`
* `RHUB_DB_TYPE`
* `RHUB_DB_USERNAME`

### HashiCorp Vault

In the HashiCorp Vault create AppRole and policy to limit access to secrets.

* `VAULT_TYPE=hashicorp`
* `VAULT_ADDR` - URL, with `https://`
* `VAULT_ROLE_ID` - AppRole `role_id`
* `VAULT_SECRET_ID` - AppRole `secret_id`

For development, you can use `file` vault that stores secrets in plain text YAML
file.

* `VAULT_TYPE=file`
* `VAULT_PATH` - path to YAML file with secrets, see example in `data/vault.yml`

Credentials are required to allow Tower Webhook Notifications to be
received by the API.  The path to the credentials in vault must be
specified using the variable below.  Don't forget to add the credentials to
vault, see example in `data/vault.yml`

* `WEBHOOK_VAULT_PATH`

## Contributing

If you want to contribute to our project, you are more then welcome - just check our [contributing guide](.github/CONTRIBUTING.md).
