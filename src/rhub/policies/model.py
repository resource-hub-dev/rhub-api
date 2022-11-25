from rhub.api import db
from rhub.api.utils import ModelMixin
from rhub.auth import model as auth_model


class Policy(db.Model, ModelMixin):
    __tablename__ = 'policies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    owner_group_id = db.Column(db.ForeignKey('auth_group.id'), primary_key=True)
    owner_group = db.relationship(auth_model.Group)
    department = db.Column(db.Text, nullable=False)
    constraint_sched_avail = db.Column(db.ARRAY(db.Text), nullable=True)
    constraint_serv_avail = db.Column(db.Numeric, nullable=True)
    constraint_limit = db.Column(db.JSON, nullable=True)
    constraint_density = db.Column(db.Text, nullable=True)
    constraint_tag = db.Column(db.ARRAY(db.Text), nullable=True)
    constraint_cost = db.Column(db.Numeric, nullable=True)
    constraint_location_id = db.Column(db.Integer, db.ForeignKey('lab_location.id'),
                                       nullable=True)
    constraint_location = db.relationship('Location')

    def to_dict(self):
        data = {}
        data['owner_group_name'] = self.owner_group.name
        data['constraint'] = {}
        for column in self.__table__.columns:
            key = column.name
            value = getattr(self, column.name)
            if 'constraint_' in key:
                data['constraint'][key[11:]] = value
            else:
                data[key] = value
        if self.constraint_location:
            data['constraint']['location'] = self.constraint_location.to_dict()
        return data

    @staticmethod
    def flatten_data(data):
        """
        Flatten constraint field in given JSON
        """
        new = {}
        for key, value in data.items():
            if key == 'constraint':
                for k, v in value.items():
                    new['constraint_' + k] = v
            else:
                new[key] = value
        return new

    @classmethod
    def from_dict(cls, data):
        return super().from_dict(cls.flatten_data(data))

    def update_from_dict(self, data):
        return super().update_from_dict(self.flatten_data(data))
