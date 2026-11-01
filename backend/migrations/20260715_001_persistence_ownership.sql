-- Additive persistence migration. Take and verify a database backup before applying.
-- Existing unowned records remain unowned and must not be assigned automatically.
-- Use `python migrate.py` from the backend directory; it applies missing changes
-- safely and records a checksum in application_schema_migrations.

ALTER TABLE datasets
    MODIFY COLUMN user_id INT NULL,
    ADD INDEX idx_datasets_user_id (user_id),
    ADD CONSTRAINT fk_datasets_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE upload_history
    MODIFY COLUMN file_size BIGINT NOT NULL;

ALTER TABLE version_history
    MODIFY COLUMN session_id VARCHAR(255) NOT NULL;

ALTER TABLE mapping_templates
    ADD COLUMN user_id INT NULL,
    ADD INDEX idx_mapping_templates_user_id (user_id),
    ADD CONSTRAINT fk_mapping_templates_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE reports
    ADD COLUMN session_id VARCHAR(255) NULL,
    ADD COLUMN report_data JSON NULL,
    ADD COLUMN generated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    ADD INDEX idx_reports_session_id (session_id);
