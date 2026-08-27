import httpx


def get_github_user(username):
    response = httpx.get(f"https://api.github.com/users/{username}")
    if response.status_code != 200:
        return None
    return response.json()


username = input("GitHub username: ")
data = get_github_user(username)

if data is None:
    print("查不到這個使用者")
else:
    print(f"Name: {data['name']}")
    print(f"Repos: {data['public_repos']}")
    print(f"Followers: {data['followers']}")
    print(f"Joined: {data['created_at']}")
