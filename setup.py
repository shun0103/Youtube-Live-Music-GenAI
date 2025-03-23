from setuptools import setup, find_packages

setup(
    name="youtube-live-music-genai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "obsws-python>=1.4.0",
        "google-api-python-client>=2.0.0",
        "google-auth>=2.0.0",
        "google-auth-oauthlib>=0.4.0",
        "google-auth-httplib2>=0.1.0",
    ],
    entry_points={
        "console_scripts": [
            "ytlive=app:main",
        ],
    },
) 