# -*- coding: utf-8 -*-
"""Bin followers by frecency

Some of the code snippet is copied as is from mastodon_archive.core.login with
minor modification to *.secret filenames. Therefore:

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
from pathlib import Path
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


def login():
    global username
    global domain

    config_dir = Path.home() / ".config/doctor-mastodon" / domain
    os.makedirs(config_dir, 0o700, exist_ok=True)

    app = core.App(
        args.user,
        scopes=('read', 'write', 'follow'),
        name="doctor-mastodon",
    )
    app.client_secret = config_dir / "client.secret"
    app.user_secret = config_dir / f"user.{username}.secret"

    pace = hasattr(args, "pace") and args.pace
    mastodon = app.login(pace)

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
