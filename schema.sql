-- HR Turnover Analyzer - Schéma de la base de données SQLite
-- Conçu pour gérer jusqu'à plusieurs centaines de collaborateurs

CREATE TABLE IF NOT EXISTS departments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS employees (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id   TEXT    NOT NULL UNIQUE,
    first_name    TEXT    NOT NULL,
    last_name     TEXT    NOT NULL,
    email         TEXT    UNIQUE,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    position      TEXT,
    hire_date     TEXT    NOT NULL,  -- format YYYY-MM-DD
    status        TEXT    NOT NULL DEFAULT 'active'
                          CHECK(status IN ('active', 'inactive')),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS exits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    exit_date   TEXT    NOT NULL,  -- format YYYY-MM-DD
    reason      TEXT    NOT NULL
                        CHECK(reason IN ('resignation', 'dismissal', 'retirement', 'end_of_contract', 'other')),
    notes       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Index pour accélérer les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department_id);
CREATE INDEX IF NOT EXISTS idx_employees_status     ON employees(status);
CREATE INDEX IF NOT EXISTS idx_employees_hire_date  ON employees(hire_date);
CREATE INDEX IF NOT EXISTS idx_employees_name       ON employees(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_exits_employee       ON exits(employee_id);
CREATE INDEX IF NOT EXISTS idx_exits_date           ON exits(exit_date);
