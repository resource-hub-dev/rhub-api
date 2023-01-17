import logging
import smtplib
import threading

import attr
import jinja2
import kombu
import kombu.mixins


logger = logging.getLogger(__name__)


@attr.s
class Notifications(kombu.mixins.ConsumerMixin):
    flask_app = attr.ib()
    broker_url = attr.ib(repr=False)
    exchange_name = attr.ib()
    smtp_server = attr.ib()
    smtp_port = attr.ib()
    email_from = attr.ib()
    email_reply_to = attr.ib()
    rhub_links = attr.ib()

    def __attrs_post_init__(self):
        self.connection = kombu.Connection(self.broker_url)
        self.exchange = kombu.Exchange(self.exchange_name, type='topic', durable=True)
        self.queue = kombu.Queue(
            'notifications',
            exchange=self.exchange,
            routing_key='#',
            durable=True,
        )

        self._j2_env = jinja2.Environment(
            loader=jinja2.PackageLoader(__name__, 'templates'),
        )
        self._j2_env.globals.update({
            'EMAIL_FROM': self.email_from,
            'EMAIL_REPLY_TO': self.email_reply_to,
            'RHUB_LINKS': self.rhub_links,
        })

        self._thread = None

    def start_thread(self):
        if not self._thread or not self._thread.is_alive():
            logger.info('Starting notifications thread.')
            self._thread = threading.Thread(target=self.run, daemon=True)
            self._thread.start()

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(
                queues=self.queue,
                callbacks=[self.on_message],
            ),
        ]

    def on_message(self, body, message):
        from rhub.auth import model as auth_model

        with self.flask_app.app_context():
            topic = message.delivery_info['routing_key']

            if topic in {'lab.cluster.create', 'lab.cluster.delete'}:
                cluster_owner = auth_model.User.query.get(body['owner_id'])
                if cluster_owner and cluster_owner.email:
                    self.send_email('email_cluster.j2', cluster_owner.email, body)
                else:
                    logger.warning(
                        f"User ID={cluster_owner.id} doesn't exist or doesn't have an "
                        "email set."
                    )

            elif topic == 'auth.user.delete':
                manager = auth_model.User.query.get(body['manager_id'])
                self.send_email('user_delete.j2', manager.email, body)

            message.ack()

    def send_email(self, template_name, email_to, data):
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as smtp:
            tpl = self._j2_env.get_template(template_name)
            email_body = tpl.render(data | {'EMAIL_TO': email_to})
            logger.debug(f'Sending email to {email_to}\n{email_body}')
            smtp.sendmail(self.email_from, [email_to], email_body)
