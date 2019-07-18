# -*- coding: utf-8 -*-

"""Console script for doctor-mastodon."""
import argparse
from enum import Enum

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from doctor_mastodon import __version__
from doctor_mastodon.util import (
    age_in_days,
    args as mastodon_archive_args,
    domain,
    get_data,
    get_list,
    list_accounts_addrm,
    login,
    username,
)
from mastodon_archive.archive import archive


def get_parser():
    """Defines options for doctor-mastodon."""
    parser = argparse.ArgumentParser(
        prog="doctor-mastodon",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="be more verbose"
    )
    parser.add_argument(
        "-V", "--version", action="version", version="%(prog)s {}".format(__version__)
    )
    # Add more arguments as needed here

    return parser


def main(args=None):
    """Console script for doctor-mastodon."""
    parser = get_parser()
    args = parser.parse_args(args)

    # Process args here
    print(
        "Replace this message by putting your code into "
        "doctor_mastodon.cli.main"
    )
    print(
        "See argparse tutorial at https://docs.python.org/3/howto/argparse.html"
    )
    # ## Make an archive

    # Before you start, install all dependencies and get an archive
    #
    # ```sh
    # pip install -r requirements.txt
    # mastodon-archive archive --with-following ashwinvis@mastodon.acc.sunet.se
    # ```
    #
    # or alternatively (if it works)


    # archive(mastodon_archive_args)


    # ## Load the archive


    df_init = pd.DataFrame(get_data()["following"])

    # Convert strings to timestamps
    df_init.created_at = df_init.created_at.apply(pd.Timestamp).dt.tz_convert(None)

    # New column: age
    df_init["age"] = df_init.created_at.apply(age_in_days)

    # New column: statuses per day to calculate volume
    df_init["statuses_per_day"] = df_init.statuses_count / df_init.age

    # Don't put bots in lists
    df_init = df_init.query("not bot")

    # Filter out bad values
    df_init.replace([np.inf, -np.inf], np.nan, inplace=True)
    # df_init.dropna(inplace=True)

    df = df_init.set_index("username")
    print(df.head())



    print("Moved users")
    for user in df.moved.dropna():
        print(user["acct"])


    # # Filter users by no. of statuses per day



    print("Plotting histogram")
    df.statuses_per_day.plot.hist(bins=10)   # , loglog=True)
    plt.xlabel("No. of statuses per day")
    plt.ylabel("No. of users")
    plt.show()





    def filter_statuses_per_day(low=0, high=np.inf):
        _ = df.sort_values("statuses_per_day", ascending=False)
        _ = _.query(f"({low} <= statuses_per_day) & (statuses_per_day < {high})")
        return _.filter(items=["id", "statuses_per_day"])





    print(df.statuses_per_day.describe())


    # ## Classify by volume




    level = [0.1, 3, 10]


    class Volumes(Enum):
        High = (level[2], np.inf)
        Mid = level[1:]
        Low = level[0:2]
        Inactive = (0, level[0])





    for v in Volumes:
        v.users = filter_statuses_per_day(*v.value)




    for v in Volumes:
        print(v.name)
        print(v.users)


    # # Organize into lists

    print("Press any key to continue?")
    input()


    mastodon = login("rw")

    for v in (Volumes.High, Volumes.Mid, Volumes.Low):
        list_id = get_list(mastodon, v.name)["id"]
        list_accounts_addrm(mastodon, list_id, v.users.id)





    # Debug
    # print([acct["id"] for acct in mastodon.list_accounts(19)])


    # # Unfollow some inactive users




    excluded = (
        "postmarketOS",
        "gokuldas2",
        "the_compiler",
        "ashwinvis",
        "gnome",
        "mozilla",
        "kinosocial"
    )
    unfollow = Volumes.Inactive.users.query(f"username not in {excluded}")
    print(unfollow)

    unfollow.id.apply(mastodon.account_unfollow)


if __name__ == "__main__":
    main()  # pragma: no cover
