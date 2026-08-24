import instaloader
import os
L = instaloader.Instaloader()

L.login(
    os.getenv("IG_USERNAME"),
    os.getenv("IG_PASSWORD")
)

profile = instaloader.Profile.from_username(
    L.context,
    "hhaarry__"
)

followers = {u.username for u in profile.get_followers()}
following = {u.username for u in profile.get_followees()}

not_following_back = following - followers

for user in sorted(not_following_back):
    print(user)