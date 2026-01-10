# BSD 2-Clause License
#
# Apprise - Push Notification Library.
# Copyright (c) 2026, Chris Caron <lead2gold@gmail.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# Feishu
#   1. Visit https://open.feishu.cn

# Custom Bot Setup
#    https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
#
# App Setup
#    https://open.feishu.cn/document/server-docs/api-call-guide/calling-process/get-access-token
#
#    Required permissions for App mode:
#    - 获取与发送单聊、群组消息 (im:message)
#    - 以应用的身份发消息 (im:message:send_as_bot)
#    - 获取用户 user ID (contact:user.base:readonly)

from json import dumps, loads
from time import time

import requests

from ..common import NotifyType
from ..locale import gettext_lazy as _
from ..utils.parse import is_email, parse_list, validate_regex
from .base import NotifyBase


class FeishuMode:
    """Feishu Notification Mode"""

    # Custom Bot Webhook Mode
    WEBHOOK = "webhook"

    # Self-built Application Mode
    APP = "app"


class NotifyFeishu(NotifyBase):
    """A wrapper for Feishu Notifications."""

    # The default descriptive name associated with the Notification
    service_name = _("Feishu")

    # The services URL
    service_url = "https://open.feishu.cn/"

    # The default secure protocol
    secure_protocol = "feishu"

    # A URL that takes you to the setup/help of the specific protocol
    setup_url = "https://appriseit.com/services/feishu/"

    # Notification URL (Webhook Mode)
    notify_url = "https://open.feishu.cn/open-apis/bot/v2/hook/{token}/"

    # App API URLs (App Mode)
    app_token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    app_message_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=email"

    # Token cache (class-level, shared across all instances)
    _tenant_token_cache = {}

    # Define object templates
    templates = (
        # Webhook Mode
        "{schema}://{token}/",
        # App Mode (requires at least one target)
        "{schema}://app/{app_id}/{app_secret}/{targets}/",
    )

    # The title is not used
    title_maxlen = 0

    # Limit is documented to be 20K message sizes.  This number safely
    # allows padding around that size.
    body_maxlen = 19985

    # Define our tokens; these are the minimum tokens required required to
    # be passed into this function (as arguments). The syntax appends any
    # previously defined in the base package and builds onto them
    template_tokens = dict(
        NotifyBase.template_tokens,
        **{
            "token": {
                "name": _("Token"),
                "type": "string",
                "private": True,
                "regex": (r"^[A-Z0-9_-]+$", "i"),
            },
            "feishu_app_id": {
                "name": _("App ID"),
                "type": "string",
                "private": True,
                "regex": (r"^cli_[a-z0-9]+$", "i"),
            },
            "feishu_app_secret": {
                "name": _("App Secret"),
                "type": "string",
                "private": True,
                "regex": (r"^[a-z0-9A-Z_-]+$", "i"),
            },
            "target_email": {
                "name": _("Target Email"),
                "type": "string",
                "map_to": "targets",
            },
            "targets": {
                "name": _("Targets"),
                "type": "list:string",
            },
        },
    )

    # Define our template arguments
    template_args = dict(
        NotifyBase.template_args,
        **{
            "token": {
                "alias_of": "token",
            },
            "feishu_app_id": {
                "alias_of": "feishu_app_id",
            },
            "feishu_app_secret": {
                "alias_of": "feishu_app_secret",
            },
            "to": {
                "alias_of": "targets",
            },
        },
    )

    def __init__(
        self,
        token=None,
        app_id=None,
        app_secret=None,
        targets=None,
        **kwargs
    ):
        """Initialize Feishu Object."""
        super().__init__(**kwargs)

        # Detect mode based on provided parameters
        if app_id and app_secret:
            # App Mode
            self.mode = FeishuMode.APP
            # Don't set token to None explicitly
            # as it may conflict with base class properties

            # Validate App ID
            self.feishu_app_id = validate_regex(
                app_id, *self.template_tokens["feishu_app_id"]["regex"]
            )
            if not self.feishu_app_id:
                msg = f"The Feishu App ID specified ({app_id}) is invalid."
                self.logger.warning(msg)
                raise TypeError(msg)

            # Validate App Secret
            self.feishu_app_secret = validate_regex(
                app_secret, *self.template_tokens["feishu_app_secret"]["regex"]
            )
            if not self.feishu_app_secret:
                msg = f"The Feishu App Secret specified ({app_secret}) is invalid."
                self.logger.warning(msg)
                raise TypeError(msg)

            # Parse targets (email addresses)
            self.targets = []
            for target in parse_list(targets):
                if is_email(target):
                    self.targets.append(target.lower())
                else:
                    self.logger.warning(
                        f"Dropped invalid email address ({target}) specified."
                    )

            if not self.targets:
                msg = "At least one valid email target is required for App mode."
                self.logger.warning(msg)
                raise TypeError(msg)

        elif token:
            # Webhook Mode
            self.mode = FeishuMode.WEBHOOK
            # Don't set app_id, app_secret, targets to None explicitly
            # as they may conflict with base class properties

            self.token = validate_regex(
                token, *self.template_tokens["token"]["regex"]
            )
            if not self.token:
                msg = f"The Feishu token specified ({token}) is invalid."
                self.logger.warning(msg)
                raise TypeError(msg)
        else:
            msg = "Either token (Webhook mode) or app_id/app_secret with targets (App mode) must be specified."
            self.logger.warning(msg)
            raise TypeError(msg)

        return

    def _get_tenant_access_token(self):
        """
        Get tenant access token for App mode.
        Implements caching with 5-minute buffer before expiration.
        """
        current_time = int(time())

        # Check cache
        if self.feishu_app_id in NotifyFeishu._tenant_token_cache:
            cached = NotifyFeishu._tenant_token_cache[self.feishu_app_id]
            if cached["expires_at"] > current_time:
                # Token is still valid
                self.logger.debug(
                    f"Using cached tenant_access_token for {self.feishu_app_id}"
                )
                return cached["token"]

        # Need to fetch new token
        self.logger.debug(f"Fetching new tenant_access_token for {self.feishu_app_id}")

        headers = {
            "User-Agent": self.feishu_app_id,
            "Content-Type": "application/json",
        }

        payload = {
            "app_id": self.feishu_app_id,
            "app_secret": self.feishu_app_secret,
        }

        try:
            r = requests.post(
                self.app_token_url,
                data=dumps(payload).encode("utf-8"),
                headers=headers,
                verify=self.verify_certificate,
                timeout=self.request_timeout,
            )

            if r.status_code != requests.codes.ok:
                self.logger.warning(
                    f"Failed to get tenant_access_token: "
                    f"HTTP {r.status_code}"
                )
                self.logger.debug(f"Response Details:\r\n{r.content}")
                return None

            response = loads(r.content)

            # Check if token was successfully retrieved
            # Response format: {"code": 0, "tenant_access_token": "...", "expire": 7200}
            if response.get("code") != 0:
                self.logger.warning(
                    f"Failed to get tenant_access_token: {response.get('msg', 'Unknown error')}"
                )
                return None

            token = response.get("tenant_access_token")
            expire = response.get("expire", 7200)  # Default 2 hours

            # Cache token with 5-minute buffer
            expires_at = current_time + expire - 300
            NotifyFeishu._tenant_token_cache[self.feishu_app_id] = {
                "token": token,
                "expires_at": expires_at,
            }

            self.logger.debug(
                f"Successfully cached tenant_access_token for {self.feishu_app_id} "
                f"(expires in {expire - 300}s)"
            )

            return token

        except requests.RequestException as e:
            self.logger.warning(
                "A connection error occurred while fetching tenant_access_token."
            )
            self.logger.debug(f"Socket Exception: {e!s}")
            return None

    def send(self, body, title="", notify_type=NotifyType.INFO, **kwargs):
        """Send our notification."""

        if self.mode == FeishuMode.WEBHOOK:
            return self._send_webhook(body, title, notify_type, **kwargs)
        else:  # App Mode
            return self._send_app(body, title, notify_type, **kwargs)

    def _send_webhook(self, body, title="", notify_type=NotifyType.INFO, **kwargs):
        """Send notification via Webhook mode."""
        # prepare our headers
        headers = {
            "User-Agent": str(self.service_name),
            "Content-Type": "application/json",
        }

        # Our Message
        payload = {
            "msg_type": "text",
            "content": {
                "text": body,
            },
        }

        self.logger.debug(
            "Feishu GET URL:"
            f" {self.notify_url} (cert_verify={self.verify_certificate!r})"
        )
        self.logger.debug(f"Feishu Payload: {payload!s}")

        # Always call throttle before any remote server i/o is made
        self.throttle()

        try:
            r = requests.post(
                self.notify_url.format(token=self.token),
                data=dumps(payload).encode("utf-8"),
                headers=headers,
                verify=self.verify_certificate,
                timeout=self.request_timeout,
                allow_redirects=self.redirects,
            )

            #
            # Sample Responses
            #
            # Valid:
            # {
            #   "code": 0,
            #   "data": {},
            #   "msg": "success"
            # }

            # Invalid (non 200 response):
            # {
            #   "code": 9499,
            #   "msg": "Bad Request",
            #   "data": {}
            # }
            if r.status_code != requests.codes.ok:
                # We had a problem
                status_str = NotifyFeishu.http_response_code_lookup(
                    r.status_code
                )

                self.logger.warning(
                    "Failed to send Feishu notification: {}{}error={}.".format(
                        status_str, ", " if status_str else "", r.status_code
                    )
                )

                self.logger.debug(
                    "Response Details:\r\n%r", (r.content or b"")[:2000]
                )

                # Return; we're done
                return False

            else:
                self.logger.info("Sent Feishu notification.")

        except requests.RequestException as e:
            self.logger.warning(
                "A Connection error occurred sending Feishu notification."
            )
            self.logger.debug(f"Socket Exception: {e!s}")

            # Return; we're done
            return False

        return True

    def _send_app(self, body, title="", notify_type=NotifyType.INFO, **kwargs):
        """Send notification via App mode."""
        # Get tenant access token
        token = self._get_tenant_access_token()
        if not token:
            self.logger.warning("Failed to get tenant_access_token, cannot send message.")
            return False

        # Prepare headers
        headers = {
            "User-Agent": self.feishu_app_id,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        # Prepare message content
        content_json = dumps({"text": body})
        payload = {
            "msg_type": "text",
            "content": content_json,
        }

        success_count = 0
        failure_count = 0

        # Send to each target
        for target in self.targets:
            # Always call throttle before any remote server i/o is made
            self.throttle()

            # Add receive_id to payload
            payload["receive_id"] = target

            self.logger.debug(
                f"Feishu App Mode: Sending to {target}"
            )
            self.logger.debug(f"Feishu Payload: {payload}")

            try:
                r = requests.post(
                    self.app_message_url,
                    data=dumps(payload).encode("utf-8"),
                    headers=headers,
                    verify=self.verify_certificate,
                    timeout=self.request_timeout,
                )

                # Parse response
                # Expected: {"code": 0, "msg": "success", "data": {...}}
                if r.status_code != requests.codes.ok:
                    status_str = NotifyFeishu.http_response_code_lookup(
                        r.status_code
                    )
                    self.logger.warning(
                        f"Failed to send Feishu notification to {target}: "
                        f"{status_str}, error={r.status_code}"
                    )
                    self.logger.debug(f"Response Details:\r\n{r.content}")
                    failure_count += 1
                    continue

                response = loads(r.content)
                if response.get("code") != 0:
                    self.logger.warning(
                        f"Failed to send Feishu notification to {target}: "
                        f"{response.get('msg', 'Unknown error')}"
                    )
                    failure_count += 1
                    continue

                # Success
                self.logger.info(f"Sent Feishu notification to {target}.")
                success_count += 1

            except requests.RequestException as e:
                self.logger.warning(
                    f"A Connection error occurred sending Feishu notification to {target}."
                )
                self.logger.debug(f"Socket Exception: {e!s}")
                failure_count += 1
                continue

        # Return True if at least one message was sent successfully
        if success_count > 0:
            self.logger.info(
                f"Feishu App Mode: Sent {success_count} message(s), "
                f"{failure_count} failed."
            )
            return True
        else:
            self.logger.warning(
                f"Feishu App Mode: Failed to send all {failure_count} message(s)."
            )
            return False

    @property
    def url_identifier(self):
        """Returns all of the identifiers that make this URL unique from
        another simliar one.

        Targets or end points should never be identified here.
        """
        if self.mode == FeishuMode.WEBHOOK:
            return (self.secure_protocol, self.token)
        else:  # App Mode
            return (self.secure_protocol, self.feishu_app_id)

    def url(self, privacy=False, *args, **kwargs):
        """Returns the URL built dynamically based on specified arguments."""

        # Prepare our parameters
        params = self.url_parameters(privacy=privacy, *args, **kwargs)

        if self.mode == FeishuMode.WEBHOOK:
            return "{schema}://{token}/?{params}".format(
                schema=self.secure_protocol,
                token=self.pprint(self.token, privacy, safe=""),
                params=NotifyFeishu.urlencode(params),
            )
        else:  # App Mode
            return "{schema}://app/{feishu_app_id}/{feishu_app_secret}/{targets}/?{params}".format(
                schema=self.secure_protocol,
                feishu_app_id=self.pprint(self.feishu_app_id, privacy, safe=""),
                feishu_app_secret=self.pprint(self.feishu_app_secret, privacy, safe=""),
                targets="/".join(
                    [NotifyFeishu.quote(target, safe="") for target in self.targets]
                ),
                params=NotifyFeishu.urlencode(params),
            )

    def __len__(self):
        """Returns the number of targets associated with this notification."""
        if self.mode == FeishuMode.WEBHOOK:
            return 1
        else:  # App Mode
            return len(self.targets) if self.targets else 1

    @staticmethod
    def parse_url(url):
        """Parses the URL and returns enough arguments that can allow us to re-
        instantiate this object."""

        # parse_url already handles getting the `user` and `password` fields
        # populated.
        results = NotifyBase.parse_url(url, verify_host=False)
        if not results:
            # We're done early as we couldn't load the results
            return results

        # Get path entries; split_path() handles unquoting content for us
        entries = NotifyFeishu.split_path(results["fullpath"])

        # Detect mode based on URL structure
        # Check if host is 'app' (for App Mode)
        if results.get("host", "").lower() == "app":
            # App Mode: feishu://app/{app_id}/{app_secret}/{email1}/{email2}/...
            if len(entries) < 3:
                # Not enough entries for App mode
                logger = NotifyFeishu.logger
                logger.warning(
                    "Invalid Feishu App mode URL; expected "
                    "feishu://app/{app_id}/{app_secret}/{targets}/"
                )
                return None

            results["app_id"] = entries[0]
            results["app_secret"] = entries[1]
            results["targets"] = entries[2:]

            # Ensure at least one target
            if not results["targets"]:
                logger = NotifyFeishu.logger
                logger.warning(
                    "Feishu App mode requires at least one target email address"
                )
                return None

            # Clear token as it's not used in App mode
            results["token"] = None

        else:
            # Webhook Mode: feishu://{token}/
            # Allow over-ride via query string
            if "token" in results["qsd"] and len(results["qsd"]["token"]):
                results["token"] = NotifyFeishu.unquote(results["qsd"]["token"])
            else:
                results["token"] = NotifyFeishu.unquote(results["host"])

            # Clear App mode fields
            results["app_id"] = None
            results["app_secret"] = None
            results["targets"] = None

        # Support the 'to' variable so that we can support targets via query string
        if "to" in results["qsd"] and len(results["qsd"]["to"]):
            to_targets = NotifyFeishu.parse_list(results["qsd"]["to"])
            if results.get("targets"):
                # Append to existing targets
                results["targets"] = results["targets"] + to_targets
            else:
                results["targets"] = to_targets

        # Support app_id and app_secret via query string (for App mode)
        if "app_id" in results["qsd"] and len(results["qsd"]["app_id"]):
            results["app_id"] = NotifyFeishu.unquote(results["qsd"]["app_id"])

        if "app_secret" in results["qsd"] and len(results["qsd"]["app_secret"]):
            results["app_secret"] = NotifyFeishu.unquote(
                results["qsd"]["app_secret"]
            )

        return results
