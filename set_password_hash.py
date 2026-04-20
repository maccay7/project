"""Print a Werkzeug password hash for use in MySQL. Run: python set_password_hash.py"""

from getpass import getpass

from werkzeug.security import generate_password_hash

pw = getpass("New password: ")
print(generate_password_hash(pw))
