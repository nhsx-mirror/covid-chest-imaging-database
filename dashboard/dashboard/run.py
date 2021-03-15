"""The NCCID dashboard server runner
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask_apscheduler import APScheduler

from dataset import Dataset
from pages import register_pages
from server import create_server

load_dotenv()

BUCKET = os.getenv("AWS_PROCESSED_BUCKET")
if BUCKET is not None:
    data_latest_path = f"s3://{BUCKET}/latest.csv"
else:
    logging.warning(
        "No bucket name provided via the AWS_PROCESSED_BUCKET env var. "
        + "Trying to load data locally."
    )
    data_latest_path = str(Path(__file__).parent / "latest.csv")

data = Dataset(data_latest_path)

server, oidc = create_server()
register_pages(data, server)

# Add authentication requirements for all dashboard pages
for view_func in server.view_functions:
    if view_func.startswith("/pages/"):
        server.view_functions[view_func] = oidc.require_login(
            server.view_functions[view_func]
        )


# Scheduled tasks
scheduler = APScheduler()
scheduler.init_app(server)
scheduler.start()


@scheduler.task(
    "interval", id="reload_data_job", hours=4, misfire_grace_time=900
)
def reload_data():
    server.logger.info("Periodic data reload starting.")
    data.load_data()


if __name__ == "__main__":
    import os

    from werkzeug.serving import run_simple

    run_simple("localhost", 8888, server, use_reloader=True)
