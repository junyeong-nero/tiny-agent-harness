import unittest

from tiny_agent_harness.channels import IngressQueue, InputChannel


class TestChannels(unittest.TestCase):
    def test_channels_public_exports_exclude_egress_queue(self):
        import tiny_agent_harness.channels as channels

        self.assertEqual(
            set(channels.__all__),
            {"IngressQueue", "InputChannel", "ListenerChannel", "OutputChannel"},
        )

    def test_input_channel_has_no_unused_fields(self):
        channel = InputChannel()

        self.assertFalse(hasattr(channel, "message_prefix"))
        self.assertFalse(hasattr(channel, "_counter"))

    def test_input_channel_uses_ingress_queue(self):
        ingress_queue = IngressQueue()
        channel = InputChannel(ingress_queue=ingress_queue)

        request = channel.queue("hello", session_id="session-1")

        self.assertEqual(request.query, "hello")
        self.assertIs(channel.dequeue(), request)

