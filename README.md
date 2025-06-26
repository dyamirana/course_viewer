# Course Viewer

A simple web application to browse HTML pages and video files from a directory.
It scans the given directory on first run and stores the structure in a SQLite
database. User progress (last opened file) is stored per user.

## Running

### Development

```bash
pip install -r requirements.txt
python -m app.server
```

### Docker

Build and start the application together with nginx using `docker-compose`:

```bash
docker-compose up --build
```

The web interface will be available on <http://localhost:8080>.

By default it serves files from the `files` directory and creates a default
user `admin` with password `admin`.
