import json
import logging

import injector
import kombu
import attr


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

        producer = self._connection.Producer()
        producer.publish(
            json.dumps(data),
            content_type='application/json',
            content_encoding='ASCII',
            exchange=self._exchange,
            routing_key=topic,
        )


class MessagingModule(injector.Module):
    def __init__(self, app):
        self.app = app

    def configure(self, binder):
        try:
            binder.bind(
                Messaging,
                to=self._create(),
                scope=injector.singleton,
            )
        except Exception:
            logger.exception(
                'Failed to create Messaging service.'
            )

    def _create(self):
        return Messaging(
            broker_url=self.app.config['RHUB_BROKER_URL'],
            exchange_name=self.app.config['RHUB_BROKER_MESSAGING_EXCHANGE'],
        )
