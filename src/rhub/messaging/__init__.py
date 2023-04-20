import json
import logging

import attr
import injector
import kombu

from .notifications import Notifications


logger = logging.getLogger(__name__)


@attr.s
class Messaging:
    broker_url = attr.ib(repr=False)
    exchange_name = attr.ib()

    def __attrs_post_init__(self):
        self._connection = kombu.Connection(self.broker_url)
        self._exchange = kombu.Exchange(self.exchange_name, type='topic', durable=True)
        with self._connection.channel() as channel:
            self._exchange.declare(channel=channel)

    def send(self, topic, msg, extra=None):
        from rhub.api.utils import date_now  # 'rhub.api' circular import

        data = extra or {}
        data['msg'] = msg
        data['date'] = date_now().isoformat()

        logger.debug(f'Sending message {msg!r} to {topic!r}, {data!r}')

        def publish_errback(ex, interval):
            logger.error(
                f'Failed to send message to {topic!r}, retry in {interval} seconds'
            )

        try:
            producer = self._connection.Producer()
            producer.publish(
                json.dumps(data),
                content_type='application/json',
                content_encoding='ASCII',
                exchange=self._exchange,
                routing_key=topic,
                retry=True,
                retry_policy=dict(
                    max_retries=3,
                    interval_start=2,
                    errback=publish_errback,
                ),
            )
        except Exception:
            logger.exception(f'Failed to send message {msg!r} to {topic!r}, {data!r}')


class MessagingModule(injector.Module):
    def __init__(self, app):
        self.app = app

    def configure(self, binder):
        try:
            binder.bind(
                Messaging,
                to=self._create_messaging(),
                scope=injector.singleton,
            )
            binder.bind(
                Notifications,
                to=self._create_notifications(),
                scope=injector.singleton,
            )
        except Exception:
            logger.exception(
                'Failed to create Messaging service.'
            )

    def _create_messaging(self):
        return Messaging(
            broker_url=self.app.config['RHUB_BROKER_URL'],
            exchange_name=self.app.config['RHUB_BROKER_MESSAGING_EXCHANGE'],
        )

    def _create_notifications(self):
        if self.app.config['SMTP_SERVER']:
            notifications = Notifications(
                flask_app=self.app,
                broker_url=self.app.config['RHUB_BROKER_URL'],
                exchange_name=self.app.config['RHUB_BROKER_MESSAGING_EXCHANGE'],
                smtp_server=self.app.config['SMTP_SERVER'],
                smtp_port=self.app.config['SMTP_PORT'],
                email_from=self.app.config['EMAIL_FROM'],
                email_reply_to=self.app.config['EMAIL_REPLY_TO'],
                email_footer_links=self.app.config['EMAIL_FOOTER_LINKS'],
            )
            notifications.start_thread()
            return notifications
        else:
            logger.info(
                'SMTP_SERVER is not configured, email notifications will be disabled'
            )
