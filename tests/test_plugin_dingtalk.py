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

# Disable logging for a cleaner testing output
import json
import logging
from unittest import mock

from helpers import AppriseURLTester
import requests

import apprise
from apprise.plugins.dingtalk import NotifyDingTalk

logging.disable(logging.CRITICAL)

# Our Testing URLs
apprise_url_tests = (
    (
        "dingtalk://",
        {
            # No Access Token specified
            "instance": TypeError,
        },
    ),
    (
        "dingtalk://a_bd_/",
        {
            # invalid Access Token
            "instance": TypeError,
        },
    ),
    (
        "dingtalk://12345678",
        {
            # access token
            "instance": NotifyDingTalk,
            # Our expected url(privacy=True) startswith() response:
            "privacy_url": "dingtalk://1...8",
        },
    ),
    (
        "dingtalk://{}/{}".format("a" * 8, "1" * 14),
        {
            # access token + phone number
            "instance": NotifyDingTalk,
        },
    ),
    (
        "dingtalk://{}/{}/invalid".format("a" * 8, "1" * 3),
        {
            # access token + 2 invalid phone numbers
            "instance": NotifyDingTalk,
        },
    ),
    (
        "dingtalk://{}/?to={}".format("a" * 8, "1" * 14),
        {
            # access token + phone number using 'to'
            "instance": NotifyDingTalk,
        },
    ),
    # Test secret via user@
    (
        "dingtalk://secret@{}/?to={}".format("a" * 8, "1" * 14),
        {
            # access token + phone number using 'to'
            "instance": NotifyDingTalk,
            # Our expected url(privacy=True) startswith() response:
            "privacy_url": "dingtalk://****@a...a",
        },
    ),
    # Test secret via secret= and token=
    (
        "dingtalk://?token={}&to={}&secret={}".format(
            "b" * 8, "1" * 14, "a" * 15
        ),
        {
            # access token + phone number using 'to'
            "instance": NotifyDingTalk,
            "privacy_url": "dingtalk://****@b...b",
        },
    ),
    # Invalid secret
    (
        "dingtalk://{}/?to={}&secret=_".format("a" * 8, "1" * 14),
        {
            "instance": TypeError,
        },
    ),
    (
        "dingtalk://{}?format=markdown".format("a" * 8),
        {
            # access token
            "instance": NotifyDingTalk,
        },
    ),
    (
        "dingtalk://{}".format("a" * 8),
        {
            "instance": NotifyDingTalk,
            # throw a bizarre code forcing us to fail to look it up
            "response": False,
            "requests_response_code": 999,
        },
    ),
    (
        "dingtalk://{}".format("a" * 8),
        {
            "instance": NotifyDingTalk,
            # Throws a series of i/o exceptions with this flag
            # is set and tests that we gracefully handle them
            "test_requests_exceptions": True,
        },
    ),
)


def test_plugin_dingtalk_urls():
    """NotifyDingTalk() Apprise URLs."""

    # Run our general tests
    AppriseURLTester(tests=apprise_url_tests).run_all()


@mock.patch("requests.post")
def test_plugin_dingtalk_payload_text(mock_post):
    """NotifyDingTalk() default text payload has matching msgtype."""

    response = requests.Request()
    response.status_code = requests.codes.ok
    mock_post.return_value = response

    obj = apprise.Apprise.instantiate("dingtalk://{}".format("a" * 8))
    assert isinstance(obj, NotifyDingTalk)
    assert obj.notify(body="hello world", title="My Title") is True

    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert payload["msgtype"] == "text"
    assert "text" in payload
    assert "markdown" not in payload
    # In text mode title_maxlen is 0, so the framework folds title into body
    assert "hello world" in payload["text"]["content"]


@mock.patch("requests.post")
def test_plugin_dingtalk_payload_markdown(mock_post):
    """NotifyDingTalk() markdown payload uses markdown msgtype and prepends
    the title as a level-1 heading to the body."""

    response = requests.Request()
    response.status_code = requests.codes.ok
    mock_post.return_value = response

    obj = apprise.Apprise.instantiate(
        "dingtalk://{}?format=markdown".format("a" * 8)
    )
    assert isinstance(obj, NotifyDingTalk)
    assert obj.notify(body="- item1\n- item2", title="Build Failed") is True

    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert payload["msgtype"] == "markdown"
    assert "markdown" in payload
    assert "text" not in payload
    # Preview chip is plain text (no leading '#')
    assert payload["markdown"]["title"] == "Build Failed"
    # Body starts with the title as an H1 so it actually renders in the chat
    assert payload["markdown"]["text"].startswith("# Build Failed\n\n")
    assert "- item1\n- item2" in payload["markdown"]["text"]


@mock.patch("requests.post")
def test_plugin_dingtalk_payload_markdown_title_with_hash(mock_post):
    """NotifyDingTalk() markdown payload does not double-prepend '#' when the
    title already starts with one, and the preview chip strips the hashes."""

    response = requests.Request()
    response.status_code = requests.codes.ok
    mock_post.return_value = response

    obj = apprise.Apprise.instantiate(
        "dingtalk://{}?format=markdown".format("a" * 8)
    )
    assert obj.notify(body="body content", title="## Already H2") is True

    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert payload["markdown"]["title"] == "Already H2"
    assert payload["markdown"]["text"].startswith("## Already H2\n\n")


@mock.patch("requests.post")
def test_plugin_dingtalk_payload_markdown_no_title(mock_post):
    """NotifyDingTalk() markdown payload falls back to app_desc for the
    preview chip when no title is given (DingTalk requires it non-empty)."""

    response = requests.Request()
    response.status_code = requests.codes.ok
    mock_post.return_value = response

    obj = apprise.Apprise.instantiate(
        "dingtalk://{}?format=markdown".format("a" * 8)
    )
    assert obj.notify(body="body only") is True

    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert payload["markdown"]["title"]  # non-empty
    assert payload["markdown"]["text"] == "body only"
