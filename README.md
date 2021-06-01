# Resource Hub API

Resource Hub API/backend service

Usage:

```sh
make init
make install
make start
```

## Requirements

The API requires other services (keycloak, database, etc) in order to function.
Some of the configuration comes from environment variables. Docker-compose in
this repository is configured to read variables from `.env` file that is created
by `make init` command.

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

* `KEYCLOAK_SERVER` - .auth-server-url from OIDC JSON
* `KEYCLOAK_RESOURCE` - .resource from OIDC JSON
* `KEYCLOAK_REALM` - .realm from OIDC JSON
* `KEYCLOAK_SECRET` - .credentials.secret from OIDC JSON
* `KEYCLOAK_ADMIN_USER` - .admin username or any user that can manage users,
  groups an roles in Keycloak (has "manage-user" and "manage-realm" roles)
* `KEYCLOAK_ADMIN_PASS` - .admin password

### PostgreSQL

In the PostgreSQL you just need to create database and user, tables and other
object are created automatically on first start.

* `DB_TYPE=postgresql`
* `DB_HOST`
* `DB_PORT`
* `DB_USERNAME`
* `DB_PASSWORD`
* `DB_DATABASE`

### HashiCorp Vault

In the HashiCorp Vault create AppRole and policy to limit access to secrets.

* `VAULT_TYPE=hashicorp`
* `VAULT_URL` - URL, with `https://`
* `VAULT_ROLE_ID` - AppRole `role_id`
* `VAULT_SECRET_ID` - AppRole `secret_id`

For development, you can use `file` vault that stores secrets in plain text YAML
file.

* `VAULT_TYPE=file`
* `VAULT_PATH` - path to YAML file with secrets, see example in `data/vault.yml`

## Contributing

If you want to contribute to our project, you are more then welcome - just check our [contributing guide](.github/CONTRIBUTING.md).
