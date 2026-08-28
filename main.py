import httpx


def github_get(path):
    try:
        response = httpx.get(f"https://api.github.com/users/{path}")
    except httpx.RequestError:
        print("網路連線出現問題")
        return None
    if response.status_code != 200:
        return None
    return response.json()

def get_github_user(username):
    return github_get(username)


def get_user_repos(username):
    return github_get(f"{username}/repos")


def print_user(user):
    print(f"Name: {user['name']}")
    print(f"Repos: {user['public_repos']}")
    print(f"Followers: {user['followers']}")
    print(f"Joined: {user['created_at']}")

username = input("GitHub username: ")
data = get_github_user(username)

if data is None:
    print("查不到這個使用者")
else:
    print_user(data)
    print("\nRepos:")
    repos = get_user_repos(username)
    if repos:
        for repo in repos:
            print(f"- {repo['name']}")
