# Credentials

The app does not need a login today. `my_app/config.py` is a tested way to load one for code that does. Credentials are never stored in the code or in Git.

`load_credentials()` reads two values, the email and the password. It looks first in environment variables, then in a private file:

- `MY_APP_API_EMAIL` and `MY_APP_API_PASSWORD`: used first, so Docker and CI need no file.
- `credentials.ini` in the `.my_app_access` folder in the user's home folder: used for any value not set in the environment. It looks like this:

```
[api]
email = your_email_here
password = your_password_here
```

If a value is in neither place, the app stops with an error that names the missing variable. The password is registered with the logger, so it is hidden in every log (see Logging above). `.gitignore` and `.dockerignore` both exclude `credentials.ini` and `.env`.

With Docker, pass the variables at run time with `-e MY_APP_API_EMAIL -e MY_APP_API_PASSWORD`. With no value after the name, Docker takes it from your shell, so the password is never typed in the command or saved in the image.
