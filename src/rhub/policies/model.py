from rhub.api import db


class Policy(db.Model):
    __tablename__ = 'policies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    department = db.Column(db.Text, nullable=False)
    constraint_sched_avail = db.Column(db.ARRAY(db.Text), nullable=True)
    constraint_serv_avail = db.Column(db.Numeric, nullable=True)
    constraint_limit = db.Column(db.JSON, nullable=True)
    constraint_density = db.Column(db.Text, nullable=True)
    constraint_tag = db.Column(db.ARRAY(db.Text), nullable=True)
    constraint_cost = db.Column(db.Numeric, nullable=True)
    constraint_location = db.Column(db.Text, nullable=True)
