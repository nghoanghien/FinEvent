"""M0 smoke pipeline.

Run after installing the package or with PYTHONPATH=src:

    python -m finevent.hello_pipeline
"""

from __future__ import annotations

import json

from finevent.config import load_config
from finevent.logging_utils import create_run_logger
from finevent.paths import ensure_directories


def main() -> None:
    config = load_config()
    ensure_directories(
        [
            config.storage.raw_dir,
            config.storage.processed_dir,
            config.storage.labels_dir,
            config.storage.vector_store_dir,
            config.logging.run_dir,
            "reports",
        ]
    )

    logger = create_run_logger(run_dir=config.logging.run_dir, config_path=config.config_path)
    logger.log(
        "hello_pipeline_started",
        config_version=config.project.config_version,
        project_name=config.project.name,
        vector_backend=config.storage.vector_backend,
    )
    logger.log("hello_pipeline_completed", status="success")

    print(
        json.dumps(
            {
                "run_id": logger.context.run_id,
                "run_log": str(logger.context.log_path),
                "status": "success",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
