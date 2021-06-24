from sqlalchemy.dialects import postgresql

from rhub.api import db, get_vault
from rhub.tower.client import Tower


class Server(db.Model):
    __tablename__ = 'tower_server'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    enabled = db.Column(db.Boolean, default=True)
    url = db.Column(db.String(256), nullable=False)
    credentials = db.Column(db.String(256), nullable=False)

    def create_tower_client(self) -> Tower:
        """
        Create Tower client.

        Returns: Tower
        Raises: RuntimeError if failed to create client due to missing
                credentials in vault
        Raises: Exception any other errors
        """
        credentials = get_vault().read(self.credentials)
        if not credentials:
            raise RuntimeError('Missing credentials in vault')
        return Tower(
            url=self.url,
            username=credentials['username'],
            password=credentials['password'],
        )


class Template(db.Model):
    __tablename__ = 'tower_template'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    server_id = db.Column(db.Integer, db.ForeignKey('tower_server.id'),
                          nullable=False)
    tower_template_id = db.Column(db.Integer, nullable=False)
    tower_template_is_workflow = db.Column(db.Boolean, nullable=False)

    jobs = db.relationship('Job', back_populates='template')
    server = db.relationship('Server')


class Job(db.Model):
    __tablename__ = 'tower_job'

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('tower_template.id'),
                            nullable=False)
    tower_job_id = db.Column(db.Integer, nullable=False)
    launched_by = db.Column(postgresql.UUID, nullable=False, index=True)

    template = db.relationship('Template')

    @property
    def server(self):
        return self.template.server
