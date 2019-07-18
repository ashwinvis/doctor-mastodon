# -*- coding: utf-8 -*-
"""Bin followers by frecency

Some of the code snippet is copied as is from mastodon_archive.core.login with
minor modification to *.secret filenames. Therefor:

Copyright (C) 2019  Ashwin Vishnu Mohanan <ashwinvis+gh@protonmail.com>
Copyright (C) 2017-2018  Alex Schroeder <alex@gnu.org>

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.

"""
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from itertools import zip_longest
from time import sleep

from mastodon import Mastodon, MastodonAPIError
from mastodon_archive import core

# FIXME: Change username and domain url
username = "ashwinvis"
domain = "mastodon.acc.sunet.se"


@dataclass
class args:
    """Mimic args for mastodon-archive CLI"""

    user = f"{username}@{domain}"
    pace = False
    skip_favourites = False
    with_mentions = True
    with_followers = True
    with_following = True


def login(scope="r"):
    global username
    global domain

    if len(scope) == "r":
        from mastodon_archive.core import read

        return read(args)
    else:
        client_secret = domain + ".rw.client.secret"
        user_secret = domain + ".rw.user." + username + ".secret"
        scopes = ["read", "write", "follow"]

        pace = hasattr(args, "pace") and args.pace

        (username, domain) = args.user.split("@")

        url = "https://" + domain
        # client_secret = domain + '.client.secret'
        # user_secret = domain + '.user.' + username + '.secret'
        mastodon = None

        if not os.path.isfile(client_secret):

            print("Registering app")
            Mastodon.create_app(
                "mastodon-organize",
                api_base_url=url,
                scopes=scopes,
                to_file=client_secret,
            )

        if not os.path.isfile(user_secret):

            print("This app needs access to your Mastodon account.")

            mastodon = Mastodon(client_id=client_secret, api_base_url=url)

            url = mastodon.auth_request_url(
                client_id=client_secret, scopes=scopes
            )

            print("Visit the following URL and authorize the app:")
            print(url)

            print("Then paste the access token here:")
            token = sys.stdin.readline().rstrip()

            try:
                # on the very first login, --pace has no effect
                mastodon.log_in(code=token, to_file=user_secret, scopes=scopes)

            except Exception as e:

                print(
                    "Sadly, that did not work. On some sites, this login mechanism"
                )
                print(
                    "(namely OAuth) seems to be broken. There is an alternative"
                )
                print(
                    "if you are willing to trust us with your password just this"
                )
                print("once. We need it just this once in order to get an access")
                print(
                    "token. We won't save it. If you don't want to try this, use"
                )
                print(
                    "Ctrl+C to quit. If you want to try it, please provide your"
                )
                print("login details.")

                sys.stdout.write("Email: ")
                sys.stdout.flush()
                email = sys.stdin.readline().rstrip()
                sys.stdout.write("Password: ")
                sys.stdout.flush()
                password = sys.stdin.readline().rstrip()

                # on the very first login, --pace has no effect
                mastodon.log_in(
                    username=email,
                    password=password,
                    to_file=user_secret,
                    scopes=scopes,
                )

        else:

            if pace:

                # in case the user kept running into a General API problem
                mastodon = Mastodon(
                    client_id=client_secret,
                    access_token=user_secret,
                    api_base_url=url,
                    ratelimit_method="pace",
                    ratelimit_pacefactor=0.9,
                    request_timeout=300,
                )

            else:

                # the defaults are ratelimit_method='wait',
                # ratelimit_pacefactor=1.1, request_timeout=300
                mastodon = Mastodon(
                    client_id=client_secret,
                    access_token=user_secret,
                    api_base_url=url,
                )

        return mastodon


def get_data():
    status_file = domain + ".user." + username + ".json"
    data = core.load(status_file, required=True, quiet=True)
    return data


def age_in_days(timestamp):
    age = datetime.utcnow() - timestamp
    return age.days


def get_list(mastodon, title):
    """Returns a list by title"""
    lst = [
        list_dict for list_dict in mastodon.lists() if list_dict["title"] == title
    ]
    if lst:
        return lst.pop()
    else:
        return mastodon.list_create(title)


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def list_accounts_addrm(mastodon, list_id, account_ids_new):
    """Fill a list with the prescribed accounts and remove accounts which are not mentioned."""

    accounts_present_first_page = mastodon.list_accounts(list_id, limit=0)
    accounts_present = mastodon.fetch_remaining(accounts_present_first_page)  # Get complete list
    account_ids_present = set(acct["id"] for acct in accounts_present)

    account_ids_new = set(account_ids_new)

    ids_to_rm = account_ids_present - account_ids_new
    ids_to_add = account_ids_new - account_ids_present

    def apply(msg, ids_to_process, func):
        """Print message and apply add / delete function on list_id"""
        nonlocal list_id
        print(msg, list_id)
        try:
            print(ids_to_process)
            func(list_id, ids_to_process)
        except MastodonAPIError as e:
            print(e)
        sleep(0.3)

    if ids_to_rm:
        apply("Deleting from list", ids_to_rm, mastodon.list_accounts_delete)
    if ids_to_add:
        apply("Adding to list", ids_to_add, mastodon.list_accounts_add)
