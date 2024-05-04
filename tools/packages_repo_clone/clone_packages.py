import os
import toml
import time
import config
import requests


APPS_REPO_ROOT = config.APPS_REPO_ROOT
GITHUB_TOKEN = config.GITHUB_TOKEN
FORGEJO_TOKEN = config.FORGEJO_TOKEN

catalog = toml.load(open(os.path.join(APPS_REPO_ROOT, "apps.toml"), encoding="utf-8"))


def generate_catalog_repo_list():
    # list the apps in the catalog

    apps_repos = []

    for app in catalog:
        url = catalog.get(app)["url"]
        name = url.split("/")[-1]  # get the last part of the URL as the repo name

        apps_repos.append([name, url])

    return apps_repos


def generate_mirror_list():
    # list the existing mirrors on our forgejo

    existing_clones = []

    data = requests.get(
        "https://git.yunohost.org/api/v1/repos/search?topic=false&includeDesc=false&priority_owner_id=17&mode=mirror"
    ).json()["data"]

    for repo in data:
        existing_clones.append(repo["name"])

    return existing_clones


def generate_mirrors():
    app_catalog = generate_catalog_repo_list()
    mirror_list = generate_mirror_list()

    for app in app_catalog:
        repo_name = app[0]
        repo_url = app[1]

        if "https://github.com/YunoHost-Apps/" not in repo_url:
            continue

        if app[0] not in mirror_list:
            print(f"A mirror for '{repo_name}' must be created.")

            api_header = {
                "Content-type": "application/json",
                "Authorization": "{FORGEJO_TOKEN}",
            }

            create_mirror_data = {
                "clone_addr": repo_url,
                "auth_token": GITHUB_TOKEN,
                "mirror": True,
                "repo_name": repo_name,
                "repo_owner": "YunoHost-Apps",
                "service": "github",
            }

            create_mirror = requests.post(
                "https://git.yunohost.org/api/v1/repos/migrate",
                headers=api_header,
                params=f"access_token={FORGEJO_TOKEN}",
                json=create_mirror_data,
            )

            if create_mirror.status_code != 201:
                if create_mirror.status_code == 409:
                    print(f"A repo named '{repo_name}' is already existing.")

                    if create_mirror.status_code == 422:
                        print(
                            f"We're rate limited. Waiting for 1 minute before continuing."
                        )
                        time.sleep(60)

                else:
                    raise Exception(
                        "Request failed:", create_mirror.status_code, create_mirror.text
                    )

            else:
                # configuring properly the new repository
                settings_mirror_data = {
                    "has_packages": False,
                    "has_projects": False,
                    "has_releases": False,
                    "has_wiki": False,
                }

                settings_mirror = requests.patch(
                    f"https://git.yunohost.org/api/v1/repos/YunoHost-Apps/{repo_name}",
                    headers=api_header,
                    params=f"access_token={FORGEJO_TOKEN}",
                    json=settings_mirror_data,
                )

                if settings_mirror.status_code != 200:
                    raise Exception("Request failed:", settings_mirror.text)
                else:
                    print("Repository cloned and configured.")
                    time.sleep(5)  # Sleeping for 5 seconds to cooldown the API


generate_mirrors()
