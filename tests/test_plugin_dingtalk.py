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

# Mock response body that satisfies every DingTalk App-mode endpoint exercised
# by the generic URL tester: `/gettoken` (errcode + access_token + expires_in),
# `/topapi/v2/user/getbymobile` (errcode + result.userid) and
# `/topapi/message/corpconversation/asyncsend_v2` (errcode).
APP_OK_RESPONSE = json.dumps({
    "errcode": 0,
    "access_token": "TOKEN_OK",
    "expires_in": 7200,
    "result": {"userid": "stub_uid"},
})

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
    # ----- App mode URL parsing -------------------------------------------
    (
        "dingtalk://app/",
        {
            # No app_key / app_secret / agent_id / targets
            "instance": TypeError,
        },
    ),
    (
        "dingtalk://app/cid",
        {
            # missing app_secret + agent_id + targets
            "instance": TypeError,
        },
    ),
    (
        "dingtalk://app/cid/sec",
        {
            # missing agent_id + targets
            "instance": TypeError,
        },
    ),
    (
        "dingtalk://app/cid/sec/123456",
        {
            # missing targets
            "instance": TypeError,
        },
    ),
    (
        "dingtalk://app/cid/sec/notanumber/userA",
        {
            # agent_id must be numeric
            "instance": TypeError,
        },
    ),
    (
        "dingtalk://app/cid/sec/123456/userA",
        {
            "instance": NotifyDingTalk,
            "privacy_url": "dingtalk://app/c...d/****/1...6/userA/",
            "requests_response_text": APP_OK_RESPONSE,
        },
    ),
    (
        "dingtalk://app/cid/sec/123456/userA/userB/13800138000/",
        {
            # userId + userId + mobile
            "instance": NotifyDingTalk,
            "requests_response_text": APP_OK_RESPONSE,
        },
    ),
    (
        "dingtalk://app/cid/sec/123456/userA/?to=userB,userC",
        {
            "instance": NotifyDingTalk,
            "requests_response_text": APP_OK_RESPONSE,
        },
    ),
    (
        "dingtalk://app/?app_key=cid&app_secret=sec&agent_id=123456"
        "&to=userA",
        {
            # All app credentials via query string
            "instance": NotifyDingTalk,
            "requests_response_text": APP_OK_RESPONSE,
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


def _make_response(body, status=200):
    resp = mock.Mock()
    resp.status_code = status
    resp.content = json.dumps(body).encode("utf-8")
    return resp


@mock.patch("requests.post")
@mock.patch("requests.get")
def test_plugin_dingtalk_app_send_text(mock_get, mock_post):
    """NotifyDingTalk() App mode sends asyncsend_v2 with text msgtype, caches
    access_token, and passes only userIds through to userid_list."""

    # Clear the class-level token cache so this test is hermetic
    NotifyDingTalk._access_token_cache.clear()

    mock_get.return_value = _make_response({
        "errcode": 0,
        "access_token": "TOKEN_AAA",
        "expires_in": 7200,
    })
    mock_post.return_value = _make_response({"errcode": 0, "errmsg": "ok"})

    obj = apprise.Apprise.instantiate(
        "dingtalk://app/cid/sec/123456/userA/userB/"
    )
    assert isinstance(obj, NotifyDingTalk)
    assert obj.notify(body="hello", title="Build OK") is True

    # access_token fetched once
    assert mock_get.call_count == 1
    assert mock_get.call_args.args[0] == NotifyDingTalk.app_token_url
    assert mock_get.call_args.kwargs["params"] == {
        "appkey": "cid",
        "appsecret": "sec",
    }

    # Exactly one asyncsend_v2 POST regardless of target count
    assert mock_post.call_count == 1
    assert mock_post.call_args.args[0] == NotifyDingTalk.app_send_url
    assert mock_post.call_args.kwargs["params"] == {
        "access_token": "TOKEN_AAA",
    }

    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert payload["agent_id"] == 123456
    assert payload["userid_list"] == "userA,userB"
    assert payload["msg"]["msgtype"] == "text"
    # title_maxlen=0 in text mode → framework folds title into body
    assert "hello" in payload["msg"]["text"]["content"]

    # Second send within token TTL should reuse cache (no extra GET)
    assert obj.notify(body="again") is True
    assert mock_get.call_count == 1


@mock.patch("requests.post")
@mock.patch("requests.get")
def test_plugin_dingtalk_app_send_markdown(mock_get, mock_post):
    """NotifyDingTalk() App mode markdown payload mirrors the webhook
    behaviour: msgtype=markdown, body prepended with title as H1, preview
    chip stripped of leading hashes."""

    NotifyDingTalk._access_token_cache.clear()
    mock_get.return_value = _make_response({
        "errcode": 0,
        "access_token": "TOKEN_MD",
        "expires_in": 7200,
    })
    mock_post.return_value = _make_response({"errcode": 0, "errmsg": "ok"})

    obj = apprise.Apprise.instantiate(
        "dingtalk://app/cidm/sec/999/userA/?format=markdown"
    )
    assert isinstance(obj, NotifyDingTalk)
    assert obj.notify(body="- a\n- b", title="Release v1") is True

    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert payload["msg"]["msgtype"] == "markdown"
    assert payload["msg"]["markdown"]["title"] == "Release v1"
    assert payload["msg"]["markdown"]["text"].startswith("# Release v1\n\n")
    assert "- a\n- b" in payload["msg"]["markdown"]["text"]


@mock.patch("requests.post")
@mock.patch("requests.get")
def test_plugin_dingtalk_app_mobile_resolution(mock_get, mock_post):
    """NotifyDingTalk() App mode resolves mobile-number targets via
    getbymobile and feeds the returned userIds to asyncsend_v2."""

    NotifyDingTalk._access_token_cache.clear()
    mock_get.return_value = _make_response({
        "errcode": 0,
        "access_token": "TOKEN_MOB",
        "expires_in": 7200,
    })

    # mock_post is called once per mobile lookup, then once for the send.
    def post_side_effect(url, *args, **kwargs):
        if url == NotifyDingTalk.app_getbymobile_url:
            mobile = json.loads(kwargs["data"])["mobile"]
            return _make_response({
                "errcode": 0,
                "result": {"userid": f"uid_for_{mobile}"},
            })
        if url == NotifyDingTalk.app_send_url:
            return _make_response({"errcode": 0, "errmsg": "ok"})
        raise AssertionError(f"unexpected POST to {url}")

    mock_post.side_effect = post_side_effect

    obj = apprise.Apprise.instantiate(
        "dingtalk://app/cid/sec/123/userA/13800138000/"
    )
    assert obj.notify(body="ping") is True

    # One getbymobile + one send
    posted_urls = [c.args[0] for c in mock_post.call_args_list]
    assert posted_urls.count(NotifyDingTalk.app_getbymobile_url) == 1
    assert posted_urls.count(NotifyDingTalk.app_send_url) == 1

    send_call = [
        c
        for c in mock_post.call_args_list
        if c.args[0] == NotifyDingTalk.app_send_url
    ][0]
    payload = json.loads(send_call.kwargs["data"])
    # parse_list sorts targets, so don't depend on order
    assert set(payload["userid_list"].split(",")) == {
        "userA",
        "uid_for_13800138000",
    }


@mock.patch("requests.post")
@mock.patch("requests.get")
def test_plugin_dingtalk_app_errcode_failure(mock_get, mock_post):
    """NotifyDingTalk() App mode returns False when asyncsend_v2 responds
    with a non-zero errcode."""

    NotifyDingTalk._access_token_cache.clear()
    mock_get.return_value = _make_response({
        "errcode": 0,
        "access_token": "TOKEN_ERR",
        "expires_in": 7200,
    })
    mock_post.return_value = _make_response({
        "errcode": 33333,
        "errmsg": "user not found",
    })

    obj = apprise.Apprise.instantiate(
        "dingtalk://app/cid/sec/123/userA/"
    )
    assert obj.notify(body="x") is False


@mock.patch("requests.post")
@mock.patch("requests.get")
def test_plugin_dingtalk_app_no_targets_after_resolve(mock_get, mock_post):
    """NotifyDingTalk() App mode aborts without calling asyncsend_v2 when
    every mobile lookup fails."""

    NotifyDingTalk._access_token_cache.clear()
    mock_get.return_value = _make_response({
        "errcode": 0,
        "access_token": "TOKEN_ZERO",
        "expires_in": 7200,
    })

    def post_side_effect(url, *args, **kwargs):
        if url == NotifyDingTalk.app_getbymobile_url:
            return _make_response({"errcode": 60121, "errmsg": "not found"})
        raise AssertionError(
            f"asyncsend_v2 should not be called when all lookups fail; "
            f"got POST to {url}"
        )

    mock_post.side_effect = post_side_effect

    obj = apprise.Apprise.instantiate(
        "dingtalk://app/cid/sec/123/13800138000/"
    )
    assert obj.notify(body="x") is False


def test_plugin_dingtalk_app_url_identifier_differs_from_webhook():
    """NotifyDingTalk() App vs Webhook URL identifiers must not collide."""

    webhook = apprise.Apprise.instantiate("dingtalk://" + "a" * 8)
    app = apprise.Apprise.instantiate(
        "dingtalk://app/cid/sec/123/userA/"
    )
    assert isinstance(webhook, NotifyDingTalk)
    assert isinstance(app, NotifyDingTalk)
    assert webhook.url_identifier != app.url_identifier
    assert app.url_identifier == ("dingtalk", "cid", "123")


def test_plugin_dingtalk_app_url_roundtrip():
    """NotifyDingTalk() App mode url() should be re-parseable into an
    equivalent object."""

    obj = apprise.Apprise.instantiate(
        "dingtalk://app/cidR/secR/4242/userA/userB/?format=markdown"
    )
    assert isinstance(obj, NotifyDingTalk)

    obj2 = apprise.Apprise.instantiate(obj.url())
    assert isinstance(obj2, NotifyDingTalk)
    assert obj.url_identifier == obj2.url_identifier
    assert obj.targets == obj2.targets


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
