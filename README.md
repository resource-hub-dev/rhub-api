# Resource Hub API

Resource Hub API/backend service

Usage:

```bash
# creates new configuration files for customization...
cp -n .env.defaults .env
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

The API requires other services (database, etc) in order to function.
Some of the configuration comes from environment variables. Docker-compose in
this repository is configured to read variables from the customized `.env` file.

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

## Authentication

### Create token

```sh
flask create-user [-g <group-name>] <user-name>
```

The API token is printed only once and then it cannot be retrieved again, so
write it down somewhere (eg. to `.env` as `TOKEN` variable).

To create admin account, run the following command:

```sh
flask create-user -g rhub-admin admin
```

### Use token

Tokens are passed to the API via `Authorization: Basic` HTTP header. Username is
`__token__` and password is the API token.

```sh
curl -u __token__:$TOKEN http://localhost:8081/v0/me
```

```python
requests.get(
    'http://localhost:8081/v0/me',
    auth=('__token__', os.environ['TOKEN']),
)
```

#### Tower

Credentials are required to allow Tower Webhook Notifications to be
received by the API.

Create admin account for use from Tower:

```sh
flask create-user -g rhub-admin tower
```

## Running quality checks

1. Install development dependencies (create a clean virtual env first, if you don't have one).
```bash
$ pip install -U -e .[dev] -r requirements.txt
```

2. SonarQube report. A link for the report will be printed on screen.
```bash
$ make scan
```

3. pip-audit report. Errors will be printed on screen.
```bash
$ tox -e pip_audit
```

4. OWASP Dependency-Check report. Report will be at `odc-reports/dependency-check-report.html`.
```bash
$ bash bin/dependency_check.sh
```

## Contributing

If you want to contribute to our project, you are more then welcome - just check our [contributing guide](.github/CONTRIBUTING.md).
