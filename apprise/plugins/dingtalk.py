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

import base64
import hashlib
import hmac
from json import dumps, loads
import re
import time

import requests

from ..common import NotifyFormat, NotifyType
from ..locale import gettext_lazy as _
from ..url import PrivacyMode
from ..utils.parse import parse_list, validate_regex
from .base import NotifyBase

# Register at https://dingtalk.com
#   - Download their PC based software as it is the only way you can create
#     a custom robot.  You can create a custom robot per group.  You will
#     be provided an access_token that Apprise will need.

# App mode setup
#   - Create a self-built enterprise application at
#     https://open-dev.dingtalk.com/. From the app's "Credentials & Basic Info"
#     page collect its `AppKey`, `AppSecret` and `AgentId` — these are the
#     three URL fields (`app_key`, `app_secret`, `agent_id`) below.
#   - Grant the app the "工作通知" / "Work Notification" message permission.
#     If you want to pass mobile numbers as targets, also grant the
#     "根据手机号获取用户" / "Look up user by mobile" permission.
#   - Add the enterprise out-of-office IP that runs Apprise to the app's
#     server IP allowlist, otherwise `/gettoken` will be refused.

# Syntax:
#  Custom robot (webhook) mode:
#    dingtalk://{access_token}/
#    dingtalk://{access_token}/{optional_phone_no}
#    dingtalk://{access_token}/{phone_no_1}/{phone_no_2}/{phone_no_N}/
#    dingtalk://{secret}@{access_token}/...
#
#  Enterprise application (app) mode:
#    dingtalk://app/{app_key}/{app_secret}/{agent_id}/{userid_or_mobile}/...

# Some Phone Number Detection
IS_PHONE_NO = re.compile(r"^\+?(?P<phone>[0-9\s)(+-]+)\s*$")


class DingTalkMode:
    """DingTalk Notification Mode."""

    # Custom Robot Webhook Mode (legacy / default)
    WEBHOOK = "webhook"

    # Self-built Enterprise Application Mode
    APP = "app"


class NotifyDingTalk(NotifyBase):
    """A wrapper for DingTalk Notifications."""

    # The default descriptive name associated with the Notification
    service_name = "DingTalk"

    # The services URL
    service_url = "https://www.dingtalk.com/"

    # All notification requests are secure
    secure_protocol = "dingtalk"

    # A URL that takes you to the setup/help of the specific protocol
    setup_url = "https://appriseit.com/services/dingtalk/"

    # DingTalk APIs (Webhook Mode)
    notify_url = "https://oapi.dingtalk.com/robot/send?access_token={token}"

    # DingTalk APIs (App Mode)
    app_token_url = "https://oapi.dingtalk.com/gettoken"
    app_send_url = (
        "https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2"
    )
    app_getbymobile_url = "https://oapi.dingtalk.com/topapi/v2/user/getbymobile"

    # access_token cache (class-level, shared across all instances).
    # Keyed by app_key; each entry: {"token": "...", "expires_at": <epoch>}
    _access_token_cache = {}

    # Do not set title_maxlen as it is set in a property value below
    # since the length varies depending if we are doing a markdown
    # based message or a text based one.
    # title_maxlen = see below @propery defined

    # Define object templates
    templates = (
        "{schema}://{token}/",
        "{schema}://{token}/{targets}/",
        "{schema}://{secret}@{token}/",
        "{schema}://{secret}@{token}/{targets}/",
        "{schema}://app/{app_key}/{app_secret}/{agent_id}/{targets}/",
    )

    # Define our template tokens
    template_tokens = dict(
        NotifyBase.template_tokens,
        **{
            "token": {
                "name": _("Token"),
                "type": "string",
                "private": True,
                "required": True,
                "regex": (r"^[a-z0-9]+$", "i"),
            },
            "secret": {
                "name": _("Secret"),
                "type": "string",
                "private": True,
                "regex": (r"^[a-z0-9]+$", "i"),
            },
            "app_key": {
                "name": _("AppKey"),
                "type": "string",
                "private": True,
                "regex": (r"^[A-Za-z0-9_-]+$",),
            },
            "app_secret": {
                "name": _("AppSecret"),
                "type": "string",
                "private": True,
                "regex": (r"^[A-Za-z0-9_-]+$",),
            },
            "agent_id": {
                "name": _("Agent ID"),
                "type": "string",
                "private": True,
                "regex": (r"^\d+$",),
            },
            "target_userid": {
                "name": _("Target DingTalk UserId"),
                "type": "string",
                "map_to": "targets",
            },
            "target_phone_no": {
                "name": _("Target Phone No"),
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
            "to": {
                "alias_of": "targets",
            },
            "token": {
                "alias_of": "token",
            },
            "secret": {
                "alias_of": "secret",
            },
            "app_key": {
                "alias_of": "app_key",
            },
            "app_secret": {
                "alias_of": "app_secret",
            },
            "agent_id": {
                "alias_of": "agent_id",
            },
        },
    )

    def __init__(
        self,
        token=None,
        targets=None,
        secret=None,
        app_key=None,
        app_secret=None,
        agent_id=None,
        **kwargs,
    ):
        """Initialize DingTalk Object."""
        super().__init__(**kwargs)

        # Mode dispatch: presence of any app-mode credential switches us into
        # App mode; otherwise we fall back to the legacy webhook mode.
        if app_key or app_secret or agent_id:
            self.mode = DingTalkMode.APP

            self.app_key = validate_regex(
                app_key, *self.template_tokens["app_key"]["regex"]
            )
            if not self.app_key:
                msg = (
                    f"An invalid DingTalk AppKey ({app_key}) was specified."
                )
                self.logger.warning(msg)
                raise TypeError(msg)

            self.app_secret = validate_regex(
                app_secret, *self.template_tokens["app_secret"]["regex"]
            )
            if not self.app_secret:
                msg = (
                    f"An invalid DingTalk AppSecret ({app_secret}) was"
                    " specified."
                )
                self.logger.warning(msg)
                raise TypeError(msg)

            self.agent_id = validate_regex(
                agent_id, *self.template_tokens["agent_id"]["regex"]
            )
            if not self.agent_id:
                msg = (
                    f"An invalid DingTalk Agent ID ({agent_id}) was specified."
                )
                self.logger.warning(msg)
                raise TypeError(msg)

            # Parse targets (each is either a DingTalk userId or a mobile
            # number; mobile numbers are resolved to userId at send time).
            self.targets = []
            for target in parse_list(targets):
                kind, value = self._classify_target(target)
                if kind is None:
                    self.logger.warning(
                        f"Dropped invalid DingTalk target ({target})"
                        " specified.",
                    )
                    continue
                self.targets.append((kind, value))

            if not self.targets:
                msg = (
                    "At least one valid DingTalk userId or mobile target is"
                    " required for App mode."
                )
                self.logger.warning(msg)
                raise TypeError(msg)

        else:
            self.mode = DingTalkMode.WEBHOOK

            self.token = validate_regex(
                token, *self.template_tokens["token"]["regex"]
            )
            if not self.token:
                msg = (
                    f"An invalid DingTalk API Token ({token}) was specified."
                )
                self.logger.warning(msg)
                raise TypeError(msg)

            self.secret = None
            if secret:
                self.secret = validate_regex(
                    secret, *self.template_tokens["secret"]["regex"]
                )
                if not self.secret:
                    msg = (
                        f"An invalid DingTalk Secret ({secret}) was specified."
                    )
                    self.logger.warning(msg)
                    raise TypeError(msg)

            # Parse our targets (phone numbers for the webhook @-mention list)
            self.targets = []
            for target in parse_list(targets):
                result = IS_PHONE_NO.match(target)
                if result:
                    result = "".join(re.findall(r"\d+", result.group("phone")))
                    if len(result) < 11 or len(result) > 14:
                        self.logger.warning(
                            f"Dropped invalid phone # ({target}) specified.",
                        )
                        continue
                    self.targets.append(result)
                    continue

                self.logger.warning(
                    f"Dropped invalid phone # ({target}) specified.",
                )

        return

    @staticmethod
    def _classify_target(target):
        """Classify an App-mode target as either a mobile number or userId.

        A target is treated as a mobile number when it matches the phone-number
        regex and its digit-only form is 11-14 chars long (same shape as the
        webhook @-mention check). Otherwise — if it is a plausible userId
        string — it is passed through verbatim.

        Returns (kind, normalized_value). kind is "mobile" or "userid"; both
        are None when the target is rejected.
        """
        if not isinstance(target, str):
            return None, None

        candidate = target.strip()
        if not candidate:
            return None, None

        phone_match = IS_PHONE_NO.match(candidate)
        if phone_match:
            digits = "".join(re.findall(r"\d+", phone_match.group("phone")))
            if 11 <= len(digits) <= 14:
                return "mobile", digits
            # Numeric blobs of the wrong length are not valid userIds either.
            return None, None

        # Treat as DingTalk userId: docs allow letters/digits/_/-/. up to 64.
        if re.match(r"^[A-Za-z0-9_.\-]{1,64}$", candidate):
            return "userid", candidate

        return None, None

    def get_signature(self):
        """Calculates time-based signature so that we can send arbitrary
        messages."""
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode("utf-8")
        str_to_sign_enc = f"{timestamp}\n{self.secret}".encode()
        hmac_code = hmac.new(
            secret_enc, str_to_sign_enc, digestmod=hashlib.sha256
        ).digest()
        signature = NotifyDingTalk.quote(base64.b64encode(hmac_code), safe="")
        return timestamp, signature

    def send(self, body, title="", notify_type=NotifyType.INFO, **kwargs):
        """Perform DingTalk Notification."""

        if self.mode == DingTalkMode.APP:
            return self._send_app(body, title, notify_type, **kwargs)
        return self._send_webhook(body, title, notify_type, **kwargs)

    def _send_webhook(
        self, body, title="", notify_type=NotifyType.INFO, **kwargs
    ):
        """Send a notification via the custom-robot webhook."""

        payload = {
            "at": {
                "atMobiles": self.targets,
                "isAtAll": False,
            },
        }

        if self.notify_format == NotifyFormat.MARKDOWN:
            # DingTalk renders `markdown.text` as the message body and uses
            # `markdown.title` only as the preview chip in the chat list /
            # push notification. The chip must be non-empty, or the API
            # silently drops the message.
            md_text = body
            if title:
                heading = (
                    title if title.lstrip().startswith("#") else f"# {title}"
                )
                md_text = f"{heading}\n\n{body}" if body else heading

            preview = title.lstrip("# \t") if title else ""
            if not preview:
                preview = self.app_desc

            payload["msgtype"] = "markdown"
            payload["markdown"] = {
                "title": preview,
                "text": md_text,
            }

        else:
            payload["msgtype"] = "text"
            payload["text"] = {
                "content": body,
            }

        # Our Notification URL
        notify_url = self.notify_url.format(token=self.token)

        params = None
        if self.secret:
            timestamp, signature = self.get_signature()
            params = {
                "timestamp": timestamp,
                "sign": signature,
            }

        # Prepare our headers
        headers = {
            "User-Agent": self.app_id,
            "Content-Type": "application/json",
        }

        # Some Debug Logging
        self.logger.debug(
            "DingTalk URL:"
            f" {notify_url} (cert_verify={self.verify_certificate})"
        )
        self.logger.debug(f"DingTalk Payload: {payload}")

        # Always call throttle before any remote server i/o is made
        self.throttle()

        try:
            r = requests.post(
                notify_url,
                data=dumps(payload),
                headers=headers,
                params=params,
                verify=self.verify_certificate,
                timeout=self.request_timeout,
                allow_redirects=self.redirects,
            )

            if r.status_code != requests.codes.ok:
                # We had a problem
                status_str = NotifyDingTalk.http_response_code_lookup(
                    r.status_code
                )

                self.logger.warning(
                    "Failed to send DingTalk notification: "
                    "{}{}error={}.".format(
                        status_str, ", " if status_str else "", r.status_code
                    )
                )

                self.logger.debug(
                    "Response Details:\r\n%r", (r.content or b"")[:2000]
                )

                return False

            else:
                self.logger.info("Sent DingTalk notification.")

        except requests.RequestException as e:
            self.logger.warning(
                "A Connection error occured sending DingTalk notification."
            )
            self.logger.debug(f"Socket Exception: {e!s}")
            return False

        return True

    def _get_access_token(self):
        """Fetch and cache an access_token for the configured DingTalk app.

        Tokens are cached at class-level keyed by app_key; we refresh 5 minutes
        before the documented expiry to avoid races with the server clock.
        Returns the token string, or None on failure.
        """
        current_time = int(time.time())

        cached = NotifyDingTalk._access_token_cache.get(self.app_key)
        if cached and cached["expires_at"] > current_time:
            self.logger.debug(
                f"Using cached DingTalk access_token for {self.app_key}"
            )
            return cached["token"]

        self.logger.debug(
            f"Fetching new DingTalk access_token for {self.app_key}"
        )

        params = {
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        headers = {
            "User-Agent": str(self.service_name),
        }

        try:
            r = requests.get(
                self.app_token_url,
                params=params,
                headers=headers,
                verify=self.verify_certificate,
                timeout=self.request_timeout,
            )

            if r.status_code != requests.codes.ok:
                self.logger.warning(
                    "Failed to fetch DingTalk access_token: "
                    f"HTTP {r.status_code}"
                )
                self.logger.debug(
                    "Response Details:\r\n%r", (r.content or b"")[:2000]
                )
                return None

            response = loads(r.content)
            if not isinstance(response, dict):
                response = {}
            if response.get("errcode", 0) != 0:
                self.logger.warning(
                    "Failed to fetch DingTalk access_token: "
                    f"{response.get('errmsg', 'unknown error')}"
                )
                return None

            token = response.get("access_token")
            if not token:
                self.logger.warning(
                    "DingTalk access_token response missing token field."
                )
                return None

            # Documented as 7200s; refresh 5 minutes early.
            expires_in = int(response.get("expires_in", 7200))
            NotifyDingTalk._access_token_cache[self.app_key] = {
                "token": token,
                "expires_at": current_time + max(60, expires_in - 300),
            }
            return token

        except requests.RequestException as e:
            self.logger.warning(
                "A Connection error occurred fetching DingTalk access_token."
            )
            self.logger.debug(f"Socket Exception: {e!s}")
            return None
        except (ValueError, TypeError) as e:
            self.logger.warning(
                "Failed to parse DingTalk access_token response."
            )
            self.logger.debug(f"Parse Exception: {e!s}")
            return None

    def _lookup_userid_by_mobile(self, access_token, mobile):
        """Resolve a mobile number to a DingTalk userId via topapi.

        Returns the userId string, or None on failure.
        """
        headers = {
            "User-Agent": str(self.service_name),
            "Content-Type": "application/json",
        }
        try:
            r = requests.post(
                self.app_getbymobile_url,
                params={"access_token": access_token},
                data=dumps({"mobile": mobile}).encode("utf-8"),
                headers=headers,
                verify=self.verify_certificate,
                timeout=self.request_timeout,
            )

            if r.status_code != requests.codes.ok:
                self.logger.warning(
                    f"DingTalk getbymobile HTTP {r.status_code} for {mobile}"
                )
                return None

            response = loads(r.content)
            if not isinstance(response, dict):
                response = {}
            if response.get("errcode", 0) != 0:
                self.logger.warning(
                    f"DingTalk getbymobile failed for {mobile}: "
                    f"{response.get('errmsg', 'unknown error')}"
                )
                return None

            result = response.get("result") or {}
            userid = result.get("userid")
            if not userid:
                self.logger.warning(
                    f"DingTalk getbymobile returned no userid for {mobile}"
                )
                return None
            return userid

        except requests.RequestException as e:
            self.logger.warning(
                f"Connection error during DingTalk getbymobile for {mobile}."
            )
            self.logger.debug(f"Socket Exception: {e!s}")
            return None
        except (ValueError, TypeError) as e:
            self.logger.warning(
                "Failed to parse DingTalk getbymobile response."
            )
            self.logger.debug(f"Parse Exception: {e!s}")
            return None

    def _resolve_targets(self, access_token):
        """Resolve self.targets into a list of DingTalk userIds.

        userId targets pass through verbatim; mobile targets are looked up
        via topapi/v2/user/getbymobile. Unresolvable targets are dropped
        with a warning.
        """
        userids = []
        for kind, value in self.targets:
            if kind == "userid":
                userids.append(value)
            elif kind == "mobile":
                uid = self._lookup_userid_by_mobile(access_token, value)
                if uid:
                    userids.append(uid)
        return userids

    def _build_app_msg(self, body, title):
        """Build the `msg` field of the asyncsend_v2 payload."""
        if self.notify_format == NotifyFormat.MARKDOWN:
            # Same rendering choice as the webhook path: DingTalk shows
            # markdown.text in chat and markdown.title only as the preview
            # chip; the chip must be non-empty.
            md_text = body
            if title:
                heading = (
                    title if title.lstrip().startswith("#") else f"# {title}"
                )
                md_text = f"{heading}\n\n{body}" if body else heading

            preview = title.lstrip("# \t") if title else ""
            if not preview:
                preview = self.app_desc

            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": preview,
                    "text": md_text,
                },
            }

        # text mode: title_maxlen=0 means the framework has already folded
        # the title into the body for us.
        return {
            "msgtype": "text",
            "text": {
                "content": body,
            },
        }

    def _send_app(self, body, title="", notify_type=NotifyType.INFO, **kwargs):
        """Send a notification via the enterprise application API."""

        access_token = self._get_access_token()
        if not access_token:
            self.logger.warning(
                "DingTalk App mode: aborting send, no access_token."
            )
            return False

        userids = self._resolve_targets(access_token)
        if not userids:
            self.logger.warning(
                "DingTalk App mode: no resolvable targets, nothing to send."
            )
            return False

        payload = {
            "agent_id": int(self.agent_id),
            "userid_list": ",".join(userids),
            "msg": self._build_app_msg(body, title),
        }

        headers = {
            "User-Agent": str(self.service_name),
            "Content-Type": "application/json",
        }

        self.logger.debug(
            f"DingTalk App URL: {self.app_send_url} "
            f"(cert_verify={self.verify_certificate})"
        )
        self.logger.debug(f"DingTalk App Payload: {payload}")

        # Always call throttle before any remote server i/o is made
        self.throttle()

        try:
            r = requests.post(
                self.app_send_url,
                params={"access_token": access_token},
                data=dumps(payload).encode("utf-8"),
                headers=headers,
                verify=self.verify_certificate,
                timeout=self.request_timeout,
                allow_redirects=self.redirects,
            )

            if r.status_code != requests.codes.ok:
                status_str = NotifyDingTalk.http_response_code_lookup(
                    r.status_code
                )
                self.logger.warning(
                    "Failed to send DingTalk (App) notification: "
                    "{}{}error={}.".format(
                        status_str, ", " if status_str else "", r.status_code
                    )
                )
                self.logger.debug(
                    "Response Details:\r\n%r", (r.content or b"")[:2000]
                )
                return False

            try:
                response = loads(r.content)
            except (ValueError, TypeError):
                response = {}
            if not isinstance(response, dict):
                response = {}

            if response.get("errcode", 0) != 0:
                self.logger.warning(
                    "Failed to send DingTalk (App) notification: "
                    f"{response.get('errmsg', 'unknown error')}"
                )
                self.logger.debug(
                    "Response Details:\r\n%r", (r.content or b"")[:2000]
                )
                return False

            self.logger.info(
                f"Sent DingTalk (App) notification to {len(userids)}"
                f" recipient(s)."
            )

        except requests.RequestException as e:
            self.logger.warning(
                "A Connection error occurred sending DingTalk (App)"
                " notification."
            )
            self.logger.debug(f"Socket Exception: {e!s}")
            return False

        return True

    @property
    def title_maxlen(self):
        """The title isn't used when not in markdown mode."""
        return (
            NotifyBase.title_maxlen
            if self.notify_format == NotifyFormat.MARKDOWN
            else 0
        )

    def url(self, privacy=False, *args, **kwargs):
        """Returns the URL built dynamically based on specified arguments."""

        # Define any arguments set
        args = {
            "format": self.notify_format,
            "overflow": self.overflow_mode,
            "verify": "yes" if self.verify_certificate else "no",
        }

        if self.mode == DingTalkMode.APP:
            target_strs = [value for _kind, value in self.targets]
            return (
                "{schema}://app/{app_key}/{app_secret}/{agent_id}/"
                "{targets}/?{args}"
            ).format(
                schema=self.secure_protocol,
                app_key=self.pprint(self.app_key, privacy, safe=""),
                app_secret=self.pprint(
                    self.app_secret,
                    privacy,
                    mode=PrivacyMode.Secret,
                    safe="",
                ),
                agent_id=self.pprint(self.agent_id, privacy, safe=""),
                targets="/".join(
                    [NotifyDingTalk.quote(x, safe="") for x in target_strs]
                ),
                args=NotifyDingTalk.urlencode(args),
            )

        return "{schema}://{secret}{token}/{targets}/?{args}".format(
            schema=self.secure_protocol,
            secret=(
                ""
                if not self.secret
                else "{}@".format(
                    self.pprint(
                        self.secret, privacy, mode=PrivacyMode.Secret, safe=""
                    )
                )
            ),
            token=self.pprint(self.token, privacy, safe=""),
            targets="/".join(
                [NotifyDingTalk.quote(x, safe="") for x in self.targets]
            ),
            args=NotifyDingTalk.urlencode(args),
        )

    @property
    def url_identifier(self):
        """Returns all of the identifiers that make this URL unique from
        another simliar one.

        Targets or end points should never be identified here.
        """
        if self.mode == DingTalkMode.APP:
            return (self.secure_protocol, self.app_key, self.agent_id)
        return (self.secure_protocol, self.secret, self.token)

    def __len__(self):
        """Returns the number of targets associated with this notification."""
        targets = len(self.targets)
        return targets if targets > 0 else 1

    @staticmethod
    def parse_url(url):
        """Parses the URL and returns enough arguments that can allow us to
        substantiate this object."""
        results = NotifyBase.parse_url(url, verify_host=False)
        if not results:
            # We're done early as we couldn't load the results
            return results

        host = (results.get("host") or "").lower()
        entries = NotifyDingTalk.split_path(results["fullpath"])

        # Query-string target overrides apply to both modes
        if "to" in results["qsd"] and len(results["qsd"]["to"]):
            extra_targets = NotifyDingTalk.parse_list(results["qsd"]["to"])
        else:
            extra_targets = []

        # ----- App mode -----------------------------------------------------
        # `dingtalk://app/{app_key}/{app_secret}/{agent_id}/{targets...}/`
        # is detected by the literal `app` host. Also triggered when any of
        # the app-mode credentials are supplied via query string.
        qsd_has_app_creds = any(
            k in results["qsd"] and results["qsd"][k]
            for k in ("app_key", "app_secret", "agent_id")
        )

        if host == "app" or qsd_has_app_creds:
            app_key = app_secret = agent_id = None
            targets = []

            if host == "app":
                # Path layout: app_key / app_secret / agent_id / targets...
                if len(entries) >= 1:
                    app_key = entries[0]
                if len(entries) >= 2:
                    app_secret = entries[1]
                if len(entries) >= 3:
                    agent_id = entries[2]
                if len(entries) >= 4:
                    targets = entries[3:]
            else:
                # Credentials supplied purely via query string; treat the
                # whole path as a target list.
                targets = entries

            # Query-string overrides take precedence
            if "app_key" in results["qsd"] and results["qsd"]["app_key"]:
                app_key = NotifyDingTalk.unquote(results["qsd"]["app_key"])
            if (
                "app_secret" in results["qsd"]
                and results["qsd"]["app_secret"]
            ):
                app_secret = NotifyDingTalk.unquote(
                    results["qsd"]["app_secret"]
                )
            if "agent_id" in results["qsd"] and results["qsd"]["agent_id"]:
                agent_id = NotifyDingTalk.unquote(results["qsd"]["agent_id"])

            targets = targets + extra_targets

            results["app_key"] = app_key
            results["app_secret"] = app_secret
            results["agent_id"] = agent_id
            results["targets"] = targets
            # Make sure webhook-mode fields aren't accidentally interpreted.
            results["token"] = None
            results["secret"] = None
            return results

        # ----- Webhook mode (legacy / default) ------------------------------
        results["token"] = NotifyDingTalk.unquote(results["host"])

        # if a user has been defined, use it's value as the secret
        if results.get("user"):
            results["secret"] = results.get("user")

        # Get our entries; split_path() looks after unquoting content for us
        # by default
        results["targets"] = entries + extra_targets

        # Support the use of the `token` keyword argument
        if "token" in results["qsd"] and len(results["qsd"]["token"]):
            results["token"] = NotifyDingTalk.unquote(results["qsd"]["token"])

        # Support the use of the `secret` keyword argument
        if "secret" in results["qsd"] and len(results["qsd"]["secret"]):
            results["secret"] = NotifyDingTalk.unquote(
                results["qsd"]["secret"]
            )

        return results
